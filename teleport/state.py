import threading

class Event:
    def __init__(self):
        self.handlers = []

    def subscribe(self, handler):
        self.handlers.append(handler)

    def unsubscribe(self, handler):
        if handler in self.handlers:
            self.handlers.remove(handler)

    def emit(self, *args, **kwargs):
        for handler in self.handlers:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                print(f"[EVENTO] Erro ao emitir evento: {e}")

class StateManager:
    def __init__(self, initial_state=None):
        self._lock = threading.Lock()
        self._state = initial_state or {}
        self.events = {
            "on_state_change": Event(),
            "on_cancel_requested": Event(),
            "on_file_grabbed": Event(),
            "on_file_dropped": Event(),
            "on_file_received": Event(),
        }

    def get(self, key, default=None):
        with self._lock:
            return self._state.get(key, default)

    def set(self, key, value):
        with self._lock:
            old_value = self._state.get(key)
            if old_value != value:
                self._state[key] = value
                # Guardar mudanca para emitir fora do lock
                change = (key, value)
            else:
                change = None
                
        if change:
            self.events["on_state_change"].emit(key, value)
            # Atalho para eventos específicos se houver
            if key == "cancel_requested" and value is True:
                self.events["on_cancel_requested"].emit()
                # reset auto
                with self._lock:
                    self._state["cancel_requested"] = False

    def update(self, new_state_dict):
        changes = []
        with self._lock:
            for k, v in new_state_dict.items():
                if self._state.get(k) != v:
                    self._state[k] = v
                    changes.append((k, v))
                    
        for k, v in changes:
            self.events["on_state_change"].emit(k, v)

    def get_all(self):
        with self._lock:
            return dict(self._state)
