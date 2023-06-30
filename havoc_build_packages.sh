#!/usr/bin/env bash

# Get deployment version
deployment_version=$(grep "deployment_version = " .havoc/havoc.version | awk '{ print $NF }')
pip_bin=./venv/bin/pip3

echo ""
echo " - Building ./HAVOC Lambda deployment packages."
if [ ! -d havoc_deploy/aws/terraform/build ]; then
    mkdir havoc_deploy/aws/terraform/build
fi
echo " - Packaging havoc_control_api/authorizer"
cd havoc_control_api/authorizer && zip -q -r ../../havoc_deploy/aws/terraform/build/authorizer.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/authorizer.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/authorizer.zip.base64sha256
echo " - Packaging havoc_control_api/manage"
cd manage && zip -q -r ../../havoc_deploy/aws/terraform/build/manage.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/manage.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/manage.zip.base64sha256
echo " - Packaging havoc_control_api/playbook_operator_control"
cd playbook_operator_control && zip -q -r ../../havoc_deploy/aws/terraform/build/playbook_operator_control.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/playbook_operator_control.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/playbook_operator_control.zip.base64sha256
echo " - Packaging havoc_control_api/playbook_operator_result"
cd playbook_operator_result && zip -q -r ../../havoc_deploy/aws/terraform/build/playbook_operator_result.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/playbook_operator_result.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/playbook_operator_result.zip.base64sha256
echo " - Packaging havoc_control_api/remote_task"
cd remote_task && zip -q -r ../../havoc_deploy/aws/terraform/build/remote_task.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/remote_task.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/remote_task.zip.base64sha256
echo " - Packaging havoc_control_api/task_control"
cd task_control && zip -q -r ../../havoc_deploy/aws/terraform/build/task_control.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/task_control.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/task_control.zip.base64sha256
echo " - Packaging havoc_control_api/task_result"
cd task_result && zip -q -r ../../havoc_deploy/aws/terraform/build/task_result.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/task_result.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/task_result.zip.base64sha256
echo " - Packaging havoc_control_api/trigger_executor"
mkdir trigger_executor/havoc
${pip_bin} --disable-pip-version-check install -q --target ./trigger_executor/havoc "havoc @ git+https://github.com/havocsh/havoc-pkg.git@${deployment_version}"
cd trigger_executor/havoc && zip -q -r ../../../havoc_deploy/aws/terraform/build/trigger_executor.zip .
cd ../.. && mkdir trigger_executor/dpath
${pip_bin} --disable-pip-version-check install -q --target ./trigger_executor/dpath dpath
cd trigger_executor/dpath && zip -q -r ../../../havoc_deploy/aws/terraform/build/trigger_executor.zip .
cd .. && zip -q -r ../../havoc_deploy/aws/terraform/build/trigger_executor.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/trigger_executor.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/trigger_executor.zip.base64sha256
cd ..
echo " - Packaging havoc_playbooks/conti_ransomware playbook"
cd havoc_playbooks && cp conti_ransomware/conti_ransomware.template ../havoc_deploy/aws/terraform/build/conti_ransomware.template
echo " - Build complete."
exit
