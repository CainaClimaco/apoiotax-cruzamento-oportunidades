from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pathlib import Path

def get_key_vault_client(url_kv):
    env_path = Path(__file__).parent / 'azure.env'
    load_dotenv(env_path)
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=url_kv, credential=credential)
    return client


def get_secrets(keys, url_kv):
    client = get_key_vault_client(url_kv)

    if isinstance(keys, str):
        return client.get_secret(keys).value
    elif isinstance(keys, list):
        secrets = {}
        for key in keys:
            try:
                secrets[key] = client.get_secret(key).value
            except Exception as e:
                secrets[key] = f"Key não encontrada: {e}"
        return secrets