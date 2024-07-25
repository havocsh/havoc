import json, base64, zlib, datetime, argparse, pprint
from configparser import ConfigParser

import havoc

init_parser = argparse.ArgumentParser(description='havoc playbook - PowerShell Empire Builtin Host Recon')

init_parser.add_argument('--profile', help='Use a specific profile from your credential file')
init_args = init_parser.parse_args()

profile = init_args.profile

def load_havoc_profiles():
    # Load the ./HAVOC profiles file
    havoc_profiles = ConfigParser()
    havoc_profiles.read('.havoc/profiles')
    return havoc_profiles

# Get api_key and secret_key
havoc_profiles = load_havoc_profiles()
if profile:
    api_key = havoc_profiles.get(profile, 'API_KEY')
    secret = havoc_profiles.get(profile, 'SECRET')
    api_region = havoc_profiles.get(profile, 'API_REGION')
    api_domain_name = havoc_profiles.get(profile, 'API_DOMAIN_NAME')
else:
    api_key = havoc_profiles.get('default', 'API_KEY')
    secret = havoc_profiles.get('default', 'SECRET')
    api_region = havoc_profiles.get('default', 'API_REGION')
    api_domain_name = havoc_profiles.get('default', 'API_DOMAIN_NAME')

h = havoc.Connect(api_region, api_domain_name, api_key, secret, api_version=1)

# Configure pretty print for displaying output.
pp = pprint.PrettyPrinter(indent=4)

deployment = h.get_deployment()
playbook_resources = ["listeners", "tasks", "portgroups", "workspace"]
delete_resources = {}

print("Enumerating active resources")
for resource in playbook_resources:
    if resource in deployment["active_resources"] and deployment["active_resources"][resource] != ["None"]:
        delete_resources[resource] = []
        print(f"Found active resources in {resource}: ")
        for r in deployment["active_resources"][resource]:
            print(f" - {r}")
            prompt = input("Would you like to terminate/delete this active resource? (Y/N): ")
            confirm = ["y", "yes"]
            if prompt.lower() in confirm:
                print("Flagging resource for removal.")
                delete_resources[resource].append(r)


listeners = delete_resources.get("listeners")
if listeners:
    for l in listeners:
        print(f"Deleting listener {l}")
        delete_listener_response = h.delete_listener(listener_name=l)
        print(delete_listener_response["outcome"])

tasks = delete_resources.get("tasks")
if tasks:
    for t in tasks:
        print(f"Terminating task {t}")
        terminate_task_response = h.kill_task(task_name=t)
        print(terminate_task_response["outcome"])

portgroups = delete_resources.get("portgroups")
if portgroups:
    for p in portgroups:
        print(f"Deleting portgroup {p}")
        delete_portgroup_response = h.delete_portgroup(portgroup_name=p)
        print(delete_portgroup_response["outcome"])

files = delete_resources.get("workspace")
if files:
    for f in files:
        file_details = f.split("/")
        path = file_details[0] + "/"
        file_name = file_details[1]
        print(f"Deleting file {f}")
        delete_file_response = h.delete_file(file_name=file_name, path=path)
        print(delete_file_response["outcome"])

print("Cleanup completed.")

