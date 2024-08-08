class Line:
    def __init__(self, unique_id, id, name, color, shape):
        self.unique_id = unique_id
        self.id = id
        self.name = name
        self.color = color
        self.shape = shape
        self.current_trips: list[Trip] = []


class Station:
    def __init__(self, id, name, lines_served):
        self.id = id
        self.name = name
        self.lines_served = lines_served


class Trip:
    def __init__(self, id):
        self.id = id
