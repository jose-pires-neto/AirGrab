class KalmanFilter2D:
    """
    Filtro de Kalman simplificado 2D para suavizar o movimento do cursor da mão
    (Posição X, Y) assumindo modelo de velocidade constante.
    """
    def __init__(self, process_variance=1e-4, measurement_variance=0.01):
        # Estado [x, y, dx, dy]
        self.state = [0.0, 0.0, 0.0, 0.0]
        # Matriz de covariância de erro inicial
        self.P = [
            [1.0, 0, 0, 0],
            [0, 1.0, 0, 0],
            [0, 0, 1.0, 0],
            [0, 0, 0, 1.0]
        ]
        self.Q = process_variance
        self.R = measurement_variance
        self.initialized = False

    def reset(self):
        self.initialized = False

    def update(self, x, y):
        if not self.initialized:
            self.state = [x, y, 0.0, 0.0]
            self.initialized = True
            return int(x), int(y)

        # 1. Predict
        # Modelo simplificado: x' = x + dx, y' = y + dy
        pred_x = self.state[0] + self.state[2]
        pred_y = self.state[1] + self.state[3]
        pred_dx = self.state[2]
        pred_dy = self.state[3]

        # Aumento da incerteza do processo
        self.P[0][0] += self.Q
        self.P[1][1] += self.Q
        self.P[2][2] += self.Q
        self.P[3][3] += self.Q

        # 2. Update (Medição)
        # Ganho de Kalman K = P / (P + R)
        K_x = self.P[0][0] / (self.P[0][0] + self.R)
        K_y = self.P[1][1] / (self.P[1][1] + self.R)
        
        # Inovação
        inn_x = x - pred_x
        inn_y = y - pred_y
        
        # Atualização do estado
        self.state[0] = pred_x + K_x * inn_x
        self.state[1] = pred_y + K_y * inn_y
        
        # Atualização da velocidade percebida (simples diferença iterativa baseada na correção)
        # Isso atua como um low-pass no delta
        self.state[2] = pred_dx + K_x * inn_x * 0.1
        self.state[3] = pred_dy + K_y * inn_y * 0.1
        
        # Atualização da Covariância
        self.P[0][0] = (1 - K_x) * self.P[0][0]
        self.P[1][1] = (1 - K_y) * self.P[1][1]

        return int(self.state[0]), int(self.state[1])
