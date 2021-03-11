from pylti1p3.tool_config import ToolConfJsonFile


class eToolConfJsonFile(ToolConfJsonFile):
    _configs_dir = None

    def update_config(self, iss=None, instance=None):
        if not instance:
            from VLE.models import Instance
            instance = Instance.objects.get(pk=1)

        if not iss:
            iss = instance.iss

        if iss in self._config:
            if instance.lti_client_id:
                self._config[iss][0]['client_id'] = instance.lti_client_id
            if instance.lti_deployment_ids:
                # Split on , and strip away the blank space to make inputting it more user friendly
                self._config[iss][0]['deployment_ids'] = [id.strip() for id in instance.lti_deployment_ids.split(',')]
            if instance.lms_url:
                print(instance.auth_login_url)
                print(instance.auth_login_url == self._config[iss][0]['auth_login_url'])
                self._config[iss][0]['auth_login_url'] = instance.auth_login_url
                self._config[iss][0]['auth_token_url'] = instance.auth_token_url
                self._config[iss][0]['key_set_url'] = instance.key_set_url
