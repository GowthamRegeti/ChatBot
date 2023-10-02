import re


def extract_session_id(session_str: str):
    pattern = r"sessions\/(.*?)\/contexts"
    match = re.search(pattern, session_str)
    if match:
        extracted_string = match.group(1)
        return extracted_string
    return ""


def get_text_from_food_dict(food_dict: dict):
    result_text = ", ".join([f"{value}: {key}" for key, value in food_dict.items()])
    return result_text


if __name__ == "__main__":
    print(get_text_from_food_dict({"samosa": 1, "chole": 2}))
    # print(extract_session_id(
    #     "projects/chatbot1-yeio/agent/sessions/eb57d09e-793a-1c84-2bd7-c5f3421c4e0d/contexts/ongoing-order"
    # ))
