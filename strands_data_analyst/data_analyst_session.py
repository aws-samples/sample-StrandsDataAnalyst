from strands_data_analyst.agent import DataAnalystAgent
from strands_data_analyst.image_handler import ImageHandler
from strands_data_analyst.database_manager import LocalDatabaseManager
from strands_data_analyst.markdown_to_pdf import markdown_to_pdf


class DataAnalystSession:
    def __init__(self, static_path):
        self.img_handler = ImageHandler(static_path, "app/static")
        
        self.data_analyst = DataAnalystAgent(img_handler=self.img_handler)
        
        self.history = []
        self.db_manager = LocalDatabaseManager()

    def message(self, content, type='text', role='assistant'):
        msg = {
            'role': role,
            'type': type,
            'content': content
        }
        self.history.append(msg)
        return msg

    def set_db(self, db_id):
        self.data_analyst.set_db(
            db_id,
            self.db_manager.init_db(db_id))
        self.history = []

    def is_new_db(self, db_id):
        return self.data_analyst.db_id != db_id

    def query(self, prompt):
        yield self.message(prompt, role='user')
        
        response = self.data_analyst.query(prompt)

        yield self.message(response['answer'])

        if 'visualization' in response:
            yield self.message(content=response['visualization'], type='image')

    def automated_data_exploration(self):
        for msg_type, msg in self.data_analyst.automated_data_exploration():
            if msg_type == 'goal':
                yield self.message(f"{msg['goal_progress']} QUESTION: {msg['goal_question']} RATIONALE: {msg['goal_rationale']}")
            
            elif msg_type == 'query_response':
                yield self.message(msg['answer'])
                if 'visualization' in msg:
                    yield self.message(content=msg['visualization'], type='image')

            elif msg_type == 'report':
                yield self.message(msg, type='document')

    def generate_report(self):
        doc = self.data_analyst.generate_report()
        return self.message(doc, type='document')
    
    def export_to_pdf(self):
        return markdown_to_pdf(self.img_handler.update_paths(self.data_analyst.document))

    def get_databases(self):
        return self.db_manager.get_list()
