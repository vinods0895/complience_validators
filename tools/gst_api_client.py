import requests

GST_API_URL = "http://localhost:8080/api/gst/validate-gstin"


def validate_gstin(gstin: str) -> dict:
    response = requests.post(
        GST_API_URL,
        json={"gstin": gstin},
        timeout=5,
    )

    if response.status_code != 200:
        return {
            "valid": False,
            "error": response.json().get("error", "UNKNOWN"),
        }

    return response.json()
