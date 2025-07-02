from typing import Any

from print_color import print


class MessageCallbackHandler:
    def __call__(self, **kwargs: Any) -> None:
        if 'message' not in kwargs:
            return
        
        message = kwargs['message']
        role = message['role']
        content = message['content']

        for content_item in content:
            if 'text' in content_item:
                print(f"[{role.title()}] {content_item['text'].strip()}\n", color="purple")

            if 'toolUse' in content_item:
                tool_use = content_item['toolUse']
                name = tool_use['name']
                print(f"[Tool] {name}", color="yellow")
                if name == 'python_repl':
                    print(tool_use['input']['code'], color="yellow")
                else:
                    for var, value in tool_use['input'].items():
                        print(f"\t- {var}: {value}", color="yellow")
                print()
            
            if 'toolResult' in content_item:
                tool_result = content_item['toolResult']
                print(f"[Tool Result] Status: {tool_result['status']}", color="blue")
                for tool_item in tool_result['content']:
                    if 'text' in tool_item:
                        print(f"{tool_item['text']}", color="blue")
                print()
