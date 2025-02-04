import json

class quiz_data_generator:
    def __init__(self):
        self.quiz_data = self.get_quiz_data()

    def get_quiz_data(self):
        quiz_data = self.read_quiz_data_file()
        return self.get_filtred_quiz_data(quiz_data)
        

    def read_quiz_data_file(self):
        try:
            with open('question_data.json', 'r') as json_file:
                return json.load(json_file).get("question_data")
        except:
            return None

    def get_filtred_quiz_data(self, quiz_data):
        try:
            filtred_quiz_data = []
            for index in range(len(quiz_data)):
                item_is_valided = self.check_quiz_data_item(quiz_data[index])
                if item_is_valided:
                    filtred_quiz_data.append(quiz_data[index])

            if len(filtred_quiz_data) > 0:
                return filtred_quiz_data
            else:
                return None
        except:
            return None

    def check_quiz_data_item(self, item):
        try:
            if (item['correct_option'] >= 0 | item['correct_option'] <= 3) & (len(item['options']) == 4):
                return True
            else:
                return False
        except:
            return False




