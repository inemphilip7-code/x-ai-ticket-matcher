from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_routes():
    res = client.get("/api/status")
    print("Status response:", res.status_code, res.json())
    assert res.status_code == 200
    
    kws = client.get("/api/keywords")
    print("Keywords response:", kws.status_code, kws.json())
    assert kws.status_code == 200
    
    logs = client.get("/api/logs")
    print("Logs count:", len(logs.json()))
    assert logs.status_code == 200

if __name__ == "__main__":
    test_routes()
    print("REALTIME BACKEND TESTS PASSED SUCCESSFULLY!")
