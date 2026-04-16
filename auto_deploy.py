# -*-coding:utf-8 -*-
import urllib.request
import json
import time
import os

# 配置常量
CONFIG_FILE = "deploy_history.json"
API_URL = "https://api.containers.back4app.com"
EXPIRATION_WINDOW = 3300  # 55分钟

HEADERS = {
    "Content-type": "application/json",
    "Cookie": "connect.sid=s%3AmWieW5Up21Zzf_gFOfHsKkVkxjkYzLGf.hjo%2Fk2TBd8btXypo77Hb401bLE%2Bh8TMNTY2pO9vhozM; __zlcmid=1X5oRJOjWiLV7jp; ab-XjkrUHOQKm=Qaz7QvmaFB!1; _gcl_au=1.1.1390214926.1776321089; landingPage=%7B%22origin%22%3A%22https%3A%2F%2Fwww.back4app.com%22%2C%22host%22%3A%22www.back4app.com%22%2C%22pathname%22%3A%22%2Flogin%22%7D; _ga=GA1.1.180305704.1776321090; b4a_amplitude_device_id=FB6pdPSNX-z2c1NdWW8_zu; __gtm_referrer=https%3A%2F%2Fdashboard.back4app.com%2F; _rdt_uuid=1776321090381.abb80e21-65cf-4a64-8e77-8fdd968bd9e5; amp_bf3379=mqtgxKuv4TvRcGSSILYUer...1jmaqpiqj.1jmaqpiqm.0.2.2; amp_bf3379_back4app.com=FB6pdPSNX-z2c1NdWW8_zu...1jmafpld0.1jmard3op.4q.6.50; _ga_FJK5KX97E0=GS2.1.s1776321089$o1$g1$t1776333263$j60$l0$h463748181; AMP_bf3379918c=JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjJGQjZwZFBTTlgtejJjMU5kV1c4X3p1JTIyJTJDJTIydXNlcklkJTIyJTNBJTIyendqYXZhMjAyNSU0MGdtYWlsLmNvbSUyMiUyQyUyMnNlc3Npb25JZCUyMiUzQTE3NzYzMjEwOTA5NzYlMkMlMjJvcHRPdXQlMjIlM0FmYWxzZSUyQyUyMmxhc3RFdmVudFRpbWUlMjIlM0ExNzc2MzMzNjMyODk3JTdE; _rdt_pn=:125~7e071fd9b023ed8f18458a73613a0834f6220bd5cc50357ba3493c6040a9ea8c|125~d8c5b4734eebc9d96d7e3e72f49735f29f62a5cb6c76c051a3c61961c02c20e8; _rdt_em=:f0944b6c79674d0478dff88a835bcf0079243d35f5faf91adf2bba1db1b06cf7,7aa513815c59723440c423d05846927d4b1d55b5561e37a1e5a025c1cf2bc080,0f1f9d9d80e0e0137467151dea38eba8ca72f64fa6d370fdce72982c858384cb,0f1f9d9d80e0e0137467151dea38eba8ca72f64fa6d370fdce72982c858384cb,0f1f9d9d80e0e0137467151dea38eba8ca72f64fa6d370fdce72982c858384cb"
}

APP_ID_MAP = {
    "29594389-d4ad-42c9-876a-adef1e3a5703": "41036cdf-e2c9-473b-bd30-4729005c006a"
}

def load_history():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f)

def list_apps():
    data = json.dumps({
        "query": "query Apps { apps { id name mainService { repository { fullName } mainServiceEnvironment { mainCustomDomain { status } } } } }"
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as f:
            res = f.read().decode("utf-8")
            j = json.loads(res)
            apps = j.get("data", {}).get("apps", [])
            ret = []
            for app in apps:
                try:
                    ret.append({
                        "app_id": app["id"],
                        "app_name": app["mainService"]["repository"]["fullName"],
                        "domain_status": app["mainService"]["mainServiceEnvironment"]["mainCustomDomain"]["status"]
                    })
                except:
                    pass
            return ret
    except Exception as e:
        print("获取失败", e)
        return []

def trigger_deploy(app_id):
    service_env_id = APP_ID_MAP.get(app_id)
    if not service_env_id:
        return False

    data = json.dumps({
        "operationName": "triggerManualDeployment",
        "variables": {"serviceEnvironmentId": service_env_id},
        "query": "mutation triggerManualDeployment($serviceEnvironmentId: String!) { triggerManualDeployment(serviceEnvironmentId: $serviceEnvironmentId) { id status } }"
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as f:
            text = f.read().decode("utf-8")
            return "error" not in text
    except:
        return False

def auto_redeploy():
    history = load_history()
    now = time.time()
    apps = list_apps()
    for app in apps:
        app_id = app["app_id"]
        last = history.get(app_id, 0)
        if now - last < EXPIRATION_WINDOW:
            continue
        if app.get("domain_status") == "EXPIRED":
            if trigger_deploy(app_id):
                history[app_id] = now
    save_history(history)

if __name__ == "__main__":
    auto_redeploy()
