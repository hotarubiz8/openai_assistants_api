import os
import time
from openai import OpenAI

# スレッドを作成し、メッセージとスレッドIDを取得するための関数
def create_and_get_thread_messages(client, initial_message):
    thread = client.beta.threads.create(messages=[{"role": "user", "content": initial_message}])
    thread_id = thread.id  # スレッドIDを取得
    messages = client.beta.threads.messages.list(thread_id).data
    return messages, thread_id  # メッセージリストとスレッドIDを返す

# メッセージの内容に引用を加える関数
def annotate_message_content(message_content, client):
    annotations = message_content.annotations
    citations = []
    for index, annotation in enumerate(annotations):
        # テキストを脚注に置き換える
        message_content.value = message_content.value.replace(annotation.text, f' [{index}]')
        # 注釈属性に基づいて引用を収集
        citation_text = get_citation_text(client, annotation, index)
        if citation_text:
            citations.append(citation_text)
    return message_content.value + '\n' + '\n'.join(citations)

# 引用テキストを取得するためのヘルパー関数
def get_citation_text(client, annotation, index):
    if file_citation := getattr(annotation, 'file_citation', None):
        cited_file = client.files.retrieve(file_citation.file_id)
        return f'[{index}] {file_citation.quote} from {cited_file.filename}'
    elif file_path := getattr(annotation, 'file_path', None):
        cited_file = client.files.retrieve(file_path.file_id)
        return f'[{index}] Click <here> to download {cited_file.filename}'
    return None

# 実行が完了するまで待つ関数
def wait_for_run_completion(client, thread_id, run_id):
    total_attempts = 20  # 状態確認の最大試行回数
    for _ in range(total_attempts):
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run.status == 'completed':
            print('検索が完了しました\n')
            return True
        elif run.status == 'failed':
            print('検索に失敗しました')
            print(run.last_error)
            return False
        time.sleep(0.5)
    return False


# ここからがプログラムの本体
os.environ["OPENAI_API_KEY"] = "OpenAIのAPIキー (sk_で始まる英数字)"
client = OpenAI()
my_assistant_id = "作成したアシスタントのID (asst_で始まる英数字)"

# スレッドを作成し、メッセージを取得
messages, thread_id = create_and_get_thread_messages(client, "中部国際空港には何時集合ですか？")
message_content = messages[0].content[0].text
annotated_message = annotate_message_content(message_content, client)
print(annotated_message)

# 実行を作成し、その完了を待つ
run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=my_assistant_id, tools=[{"type": "retrieval"}])
if wait_for_run_completion(client, thread_id, run.id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    print(messages.data[0].content[0].text.value)

print('\n終了')
