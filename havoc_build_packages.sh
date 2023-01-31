#!/usr/bin/env bash

echo ""
echo "Building ./HAVOC Lambda deployment packages."
if [ ! -d havoc_deploy/aws/terraform/build ]; then
    mkdir havoc_deploy/aws/terraform/build
fi
echo " - packaging havoc_control_api/authorizer"
cd havoc_control_api/authorizer && zip -q -r ../../havoc_deploy/aws/terraform/build/authorizer.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/authorizer.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/authorizer.zip.base64sha256
echo " - packaging havoc_control_api/manage"
cd manage && zip -q -r ../../havoc_deploy/aws/terraform/build/manage.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/manage.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/manage.zip.base64sha256
echo " - packaging havoc_control_api/remote_task"
cd remote_task && zip -q -r ../../havoc_deploy/aws/terraform/build/remote_task.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/remote_task.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/remote_task.zip.base64sha256
echo " - packaging havoc_control_api/task_control"
cd task_control && zip -q -r ../../havoc_deploy/aws/terraform/build/task_control.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/task_control.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/task_control.zip.base64sha256
echo " - packaging havoc_control_api/task_result"
cd task_result && zip -q -r ../../havoc_deploy/aws/terraform/build/task_result.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/build/task_result.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/build/task_result.zip.base64sha256
cd ..
echo "Build complete."
exit
