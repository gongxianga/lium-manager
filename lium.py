#!/usr/bin/env python3
"""Lium GPU 租用管理工具"""

import os
import sys
import json
import requests
from typing import Optional

BASE_URL = "https://lium.io/api"
CONFIG_FILE = os.path.expanduser("~/.lium_config.json")


# ─── 配置管理 ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_FILE, 0o600)


def get_api_key() -> str:
    config = load_config()
    if config.get("api_key"):
        return config["api_key"]
    print("\n未找到 API Key，请先设置。")
    print("获取方式：登录 lium.io -> Settings -> API Keys")
    key = input("请输入 API Key: ").strip()
    if not key:
        print("API Key 不能为空")
        sys.exit(1)
    config["api_key"] = key
    save_config(config)
    print("API Key 已保存。")
    return key


# ─── HTTP 请求 ────────────────────────────────────────────────────────────────

def api_get(path: str, params: dict = None) -> Optional[dict]:
    api_key = get_api_key()
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=15)
        if r.status_code == 401:
            print("认证失败，请检查 API Key 是否正确。")
            return None
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        print("网络连接失败，请检查网络。")
        return None
    except requests.exceptions.Timeout:
        print("请求超时，请重试。")
        return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None


def api_post(path: str, body: dict = None) -> Optional[dict]:
    api_key = get_api_key()
    headers = {"X-API-Key": api_key, "Accept": "application/json", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{BASE_URL}{path}", headers=headers, json=body or {}, timeout=15)
        if r.status_code == 401:
            print("认证失败，请检查 API Key 是否正确。")
            return None
        if r.status_code in (200, 201):
            return r.json() if r.text else {"ok": True}
        print(f"请求失败 [{r.status_code}]: {r.text}")
        return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None


def api_delete(path: str) -> bool:
    api_key = get_api_key()
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    try:
        r = requests.delete(f"{BASE_URL}{path}", headers=headers, timeout=15)
        if r.status_code in (200, 204):
            return True
        print(f"删除失败 [{r.status_code}]: {r.text}")
        return False
    except Exception as e:
        print(f"请求失败: {e}")
        return False


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def hr():
    print("─" * 60)


def pause():
    input("\n按 Enter 返回主菜单...")


def fmt_price(val) -> str:
    if val is None:
        return "N/A"
    return f"${float(val):.4f}/hr"


def fmt_gpu(item: dict) -> str:
    name = item.get("machine_name") or item.get("gpu_name") or "未知GPU"
    count = item.get("gpu_count") or item.get("num_gpus") or 1
    return f"{count}x {name}"


def print_executor(idx: int, e: dict):
    uuid = e.get("uuid") or e.get("id") or "?"
    gpu = fmt_gpu(e)
    price = fmt_price(e.get("price") or e.get("price_per_hour"))
    location = e.get("location") or e.get("country") or ""
    ram = e.get("ram_gb") or e.get("memory_gb") or ""
    ram_str = f"  内存: {ram}GB" if ram else ""
    loc_str = f"  地区: {location}" if location else ""
    print(f"  [{idx}] {gpu}  价格: {price}{ram_str}{loc_str}")
    print(f"       UUID: {uuid}")


# ─── 功能模块 ─────────────────────────────────────────────────────────────────

def list_available():
    """查看可用机器"""
    print("\n=== 查看可用机器 ===")
    hr()

    params = {}

    # 筛选条件
    print("可设置筛选条件（直接回车跳过）：")
    gpu_name = input("GPU 型号（如 RTX4090, A100）: ").strip()
    if gpu_name:
        params["machine_names"] = gpu_name

    gpu_min = input("最少 GPU 数量: ").strip()
    if gpu_min.isdigit():
        params["gpu_count_gte"] = int(gpu_min)

    gpu_max = input("最多 GPU 数量: ").strip()
    if gpu_max.isdigit():
        params["gpu_count_lte"] = int(gpu_max)

    price_max = input("最高价格（美元/小时）: ").strip()
    try:
        if price_max:
            params["price_lte"] = float(price_max)
    except ValueError:
        pass

    price_min = input("最低价格（美元/小时）: ").strip()
    try:
        if price_min:
            params["price_gte"] = float(price_min)
    except ValueError:
        pass

    params["size"] = 50

    print("\n查询中...")
    data = api_get("/executors", params=params)
    if data is None:
        pause()
        return

    items = data if isinstance(data, list) else data.get("items") or data.get("data") or data.get("executors") or []

    if not items:
        print("没有找到符合条件的机器。")
        pause()
        return

    # 调试：打印第一条所有字段名和值
    if items:
        print("[调试] 第一条记录所有字段:")
        for k, v in items[0].items():
            print(f"  {k}: {v}")

    print(f"\n找到 {len(items)} 台可用机器：")
    hr()
    for i, e in enumerate(items, 1):
        print_executor(i, e)
    hr()
    pause()


def rent_machine():
    """租用机器"""
    print("\n=== 租用机器 ===")
    hr()

    # 先查询可用机器
    params = {}
    print("设置筛选条件查找机器（直接回车跳过）：")
    gpu_name = input("GPU 型号（如 RTX4090, A100）: ").strip()
    if gpu_name:
        params["machine_names"] = gpu_name

    gpu_count = input("GPU 数量: ").strip()
    if gpu_count.isdigit():
        params["gpu_count_gte"] = int(gpu_count)
        params["gpu_count_lte"] = int(gpu_count)

    price_max = input("最高价格（美元/小时）: ").strip()
    try:
        if price_max:
            params["price_lte"] = float(price_max)
    except ValueError:
        pass

    params["size"] = 20

    print("\n查询中...")
    data = api_get("/executors", params=params)
    if data is None:
        pause()
        return

    items = data if isinstance(data, list) else data.get("items") or data.get("data") or []

    if not items:
        print("没有找到符合条件的机器。")
        pause()
        return

    print(f"\n找到 {len(items)} 台可用机器：")
    hr()
    for i, e in enumerate(items, 1):
        print_executor(i, e)
    hr()

    choice = input("选择要租用的机器编号（输入 0 取消）: ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(items):
        print("编号无效。")
        pause()
        return

    executor = items[idx]
    uuid = executor.get("uuid") or executor.get("id")
    if not uuid:
        print("无法获取机器 UUID。")
        pause()
        return

    print(f"\n已选择: {fmt_gpu(executor)}  价格: {fmt_price(executor.get('price') or executor.get('price_per_hour'))}")
    hr()

    # 租用参数
    print("设置租用参数：")
    image = input("Docker 镜像（默认: ubuntu:22.04）: ").strip() or "ubuntu:22.04"
    ssh_key = input("SSH 公钥（可选，回车跳过）: ").strip()
    hours = input("租用时长（小时，可选）: ").strip()

    body = {"image": image}
    if ssh_key:
        body["ssh_public_key"] = ssh_key
    try:
        if hours:
            body["duration_hours"] = float(hours)
    except ValueError:
        pass

    confirm = input(f"\n确认租用？(y/n): ").strip().lower()
    if confirm != "y":
        print("已取消。")
        pause()
        return

    print("发送租用请求...")
    result = api_post(f"/executors/{uuid}/rent", body)
    if result:
        print("\n租用成功！")
        pod_id = result.get("id") or result.get("pod_id") or result.get("uuid")
        if pod_id:
            print(f"Pod ID: {pod_id}")
        print("详细信息：")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    pause()


def list_my_pods():
    """查看我的 Pods"""
    print("\n=== 我的 Pods ===")
    hr()

    print("查询中...")
    data = api_get("/pods")
    if data is None:
        pause()
        return

    items = data if isinstance(data, list) else data.get("items") or data.get("data") or []

    if not items:
        print("当前没有租用中的机器。")
        pause()
        return

    print(f"共 {len(items)} 个 Pod：")
    hr()
    for i, pod in enumerate(items, 1):
        pod_id = pod.get("id") or pod.get("uuid") or "?"
        status = pod.get("status") or pod.get("state") or "未知"
        gpu = fmt_gpu(pod)
        price = fmt_price(pod.get("price") or pod.get("price_per_hour"))
        ip = pod.get("ip") or pod.get("host") or ""
        ip_str = f"  IP: {ip}" if ip else ""
        print(f"  [{i}] ID: {pod_id}")
        print(f"       状态: {status}  GPU: {gpu}  价格: {price}{ip_str}")
    hr()
    pause()


def manage_pod():
    """管理已有 Pod（停止/重启）"""
    print("\n=== 管理 Pod ===")
    hr()

    print("查询 Pods 中...")
    data = api_get("/pods")
    if data is None:
        pause()
        return

    items = data if isinstance(data, list) else data.get("items") or data.get("data") or []

    if not items:
        print("当前没有租用中的机器。")
        pause()
        return

    print(f"共 {len(items)} 个 Pod：")
    hr()
    for i, pod in enumerate(items, 1):
        pod_id = pod.get("id") or pod.get("uuid") or "?"
        status = pod.get("status") or pod.get("state") or "未知"
        gpu = fmt_gpu(pod)
        print(f"  [{i}] {gpu}  状态: {status}  ID: {pod_id}")
    hr()

    choice = input("选择 Pod 编号（输入 0 取消）: ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(items):
        print("编号无效。")
        pause()
        return

    pod = items[idx]
    pod_id = pod.get("id") or pod.get("uuid")

    print(f"\n选中: {fmt_gpu(pod)}  ID: {pod_id}")
    print("操作：")
    print("  [1] 停止并删除")
    print("  [2] 重启")
    print("  [3] 安排定时删除")
    print("  [0] 取消")

    op = input("选择操作: ").strip()

    if op == "1":
        confirm = input("确认删除该 Pod？(y/n): ").strip().lower()
        if confirm == "y":
            if api_delete(f"/pods/{pod_id}"):
                print("Pod 已成功删除。")
            else:
                print("删除失败。")

    elif op == "2":
        result = api_post(f"/pods/{pod_id}/reboot")
        if result is not None:
            print("重启指令已发送。")
        else:
            print("重启失败。")

    elif op == "3":
        delay = input("多少小时后删除？: ").strip()
        body = {}
        try:
            if delay:
                body["hours"] = float(delay)
        except ValueError:
            pass
        result = api_post(f"/pods/{pod_id}/schedule-removal", body)
        if result is not None:
            print("已设置定时删除。")
        else:
            print("设置失败。")

    pause()


def set_api_key():
    """修改 API Key"""
    print("\n=== 修改 API Key ===")
    config = load_config()
    current = config.get("api_key", "")
    if current:
        print(f"当前 API Key: {current[:8]}{'*' * 20}")
    key = input("输入新的 API Key（回车取消）: ").strip()
    if key:
        config["api_key"] = key
        save_config(config)
        print("API Key 已更新。")
    pause()


# ─── 主菜单 ───────────────────────────────────────────────────────────────────

def main():
    while True:
        print()
        print("╔══════════════════════════════════╗")
        print("║      Lium GPU 租用管理工具        ║")
        print("╠══════════════════════════════════╣")
        print("║  [1] 查看可用机器                 ║")
        print("║  [2] 租用机器                     ║")
        print("║  [3] 查看我的 Pods                ║")
        print("║  [4] 管理 Pod（停止/重启）        ║")
        print("║  [5] 修改 API Key                 ║")
        print("║  [0] 退出                         ║")
        print("╚══════════════════════════════════╝")

        choice = input("请选择: ").strip()

        if choice == "1":
            list_available()
        elif choice == "2":
            rent_machine()
        elif choice == "3":
            list_my_pods()
        elif choice == "4":
            manage_pod()
        elif choice == "5":
            set_api_key()
        elif choice == "0":
            print("再见！")
            break
        else:
            print("无效选项，请重试。")


if __name__ == "__main__":
    main()
