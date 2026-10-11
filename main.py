import httpx
from model import JobApplication
from mail_fetcher import email_list

URL = "http://localhost:8080/v1/chat/completions"
MODEL = "mlx-community/Qwen3-8B-4bit"
SYSTEM_PROMPT = f"""You are an email classifier. You look at the given subject line first and then
classify if it is worth looking at the entire email. If yes, reply continue without any line breaks. Then I'll provide you the whole email.
You look at the sender's email, the subject line and the body of the email and figure out the 
company and whether it is an application submitted, a rejection or an acceptance. It should be in 
the format: {JobApplication().model_dump_json()} but with the company details mentioned in the email. 
If the email is not an application email just reply None without any line breaks."""
MAX_STEPS = 5

def call_llm(messages):
    llm_json = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 3000
    }
    response = httpx.post(URL, json =llm_json, timeout=300)
    choice = response.json()["choices"][0]
    return choice["message"]


def agent():

    emails = email_list()

    for email in emails:
        print(email.subject)
        messages = [{"role":"system", "content":SYSTEM_PROMPT},
                    {"role":"user", "content":email.subject}]

        #for step in range(1, MAX_STEPS+1):
        try:
            reply = call_llm(messages)
            print(reply['content'])
            if reply['content'].strip() == "continue":
                messages.append({"role":"classifier", "content":reply["content"]})
                messages.append({"role":"user","content":email.model_dump_json()})
                reply2 = call_llm(messages)
                print(reply2['content'])
                if reply2['content'].strip() != "None":
                    ja = JobApplication.model_validate_json(reply2['content'])
                    print(ja)
        except Exception as e:
            print(e)

if __name__ == "__main__":
    agent()