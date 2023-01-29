#!/usr/bin/env bash

echo ""
echo "Building ./HAVOC Lambda deployment packages."
echo " - packaging havoc_control_api/authorizer"
cd havoc_control_api/authorizer && zip -q -r ../../havoc_deploy/aws/terraform/authorizer.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/authorizer.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/authorizer.zip.base64sha256
echo " - packaging havoc_control_api/manage"
cd manage && zip -q -r ../../havoc_deploy/aws/terraform/manage.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/manage.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/manage.zip.base64sha256
echo " - packaging havoc_control_api/remote_task"
cd remote_task && zip -q -r ../../havoc_deploy/aws/terraform/remote_task.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/remote_task.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/remote_task.zip.base64sha256
echo " - packaging havoc_control_api/task_control"
cd task_control && zip -q -r ../../havoc_deploy/aws/terraform/task_control.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/task_control.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/task_control.zip.base64sha256
echo " - packaging havoc_control_api/task_result"
cd task_result && zip -q -r ../../havoc_deploy/aws/terraform/task_result.zip .
cd .. && openssl dgst -sha256 -binary ../havoc_deploy/aws/terraform/task_result.zip | openssl enc -base64 > ../havoc_deploy/aws/terraform/task_result.zip.base64sha256
cd ..
echo "Build complete."
exit
