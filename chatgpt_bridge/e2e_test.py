"""端到端测试：模拟 Chrome 扩展完成一次 ChatGPT 问答链路"""
import requests
import time
import json

BRIDGE = "http://localhost:8799"


def test_roundtrip():
    text = "测试问题 __chrome_ext_e2e__"
    # 1. 提交问题
    r = requests.post(f"{BRIDGE}/prompt", json={"text": text})
    print(f"/prompt status={r.status_code} body={r.text}")
    task_id = r.json()["task_id"]

    # 2. 模拟扩展轮询 /pending
    time.sleep(0.5)
    r = requests.get(f"{BRIDGE}/pending")
    print(f"/pending body={r.text}")
    task = r.json()
    assert task["task_id"] == task_id
    assert task["text"] == text

    # 3. 模拟扩展完成
    answer = "这是模拟的 ChatGPT 回答 __chrome_ext_e2e_answer__"
    r = requests.post(f"{BRIDGE}/complete", json={
        "task_id": task_id,
        "text": answer,
        "title": "Chrome扩展E2E测试",
    })
    print(f"/complete status={r.status_code} body={r.text}")
    assert r.json()["success"]

    # 4. 查询 /result
    time.sleep(0.5)
    r = requests.get(f"{BRIDGE}/result", params={"task_id": task_id})
    print(f"/result body={r.text}")
    assert r.json()["done"]
    assert answer in r.json()["text"]

    # 5. 等待索引后检索
    time.sleep(2)
    r = requests.post(f"http://localhost:8766/api/retrieve/search", json={
        "query": "__chrome_ext_e2e_answer__",
        "limit": 5,
    })
    print(f"第二大脑检索 body={r.text[:300]}")
    assert "chrome_ext_e2e" in r.text

    print("\n✅ E2E 全部通过：WorkBuddy -> 桥 -> 扩展 -> 桥 -> 第二大脑")


if __name__ == "__main__":
    test_roundtrip()
