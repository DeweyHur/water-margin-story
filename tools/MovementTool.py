import random

class MovementTool:
    def __init__(self):
        self.random_number = random.randint(1, 100)

    def generate_random_number(self):
        return self.random_number

movement_tool = MovementTool()

if __name__ == '__main__':
    print(movement_tool.generate_random_number())