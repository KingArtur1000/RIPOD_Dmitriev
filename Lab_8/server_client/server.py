import xmlrpc.server
import networkx as nx

class PlannerComponent:
    def ping(self):
        """Служебный метод для проверки связи"""
        return "pong"

    def calculate_plan(self, edges_list, p):
        G = nx.DiGraph()
        edges = []
        for pair in edges_list:
            try:
                u, v = pair.split("-")
                edges.append((u.strip(), v.strip()))
            except ValueError:
                pass
        
        G.add_edges_from(edges)
        if not nx.is_directed_acyclic_graph(G):
            return {"error": "Граф содержит циклы!"}

        # Алгоритм List Scheduling (скрыт от клиента)
        priorities = {}
        for node in reversed(list(nx.topological_sort(G))):
            succs = list(G.successors(node))
            priorities[node] = 1 if not succs else 1 + max(priorities[s] for s in succs)

        proc_free_time = [0] * p
        assigned_proc = {}
        start_time = {}
        end_time = {}
        scheduled = set()

        while len(scheduled) < len(G.nodes()):
            ready = [n for n in G.nodes() if n not in scheduled and all(pr in scheduled for pr in G.predecessors(n))]
            if not ready: break
            
            ready.sort(key=lambda x: (-priorities[x], str(x)))
            min_time = min(proc_free_time)
            free_procs = [i for i in range(p) if proc_free_time[i] == min_time]

            for proc in free_procs:
                if not ready: break
                task = ready.pop(0)
                preds = list(G.predecessors(task))
                dep_time = max([end_time[pr] for pr in preds]) if preds else 0
                
                st = max(proc_free_time[proc], dep_time)
                et = st + 1
                
                proc_free_time[proc] = et
                assigned_proc[task] = proc
                start_time[task] = st
                end_time[task] = et
                scheduled.add(task)

        return {
            "assigned_proc": assigned_proc,
            "start_time": start_time,
            "end_time": end_time,
            "makespan": max(end_time.values()) if end_time else 0
        }

def start_com_server():
    # Используем 127.0.0.1 вместо localhost для скорости
    server = xmlrpc.server.SimpleXMLRPCServer(("127.0.0.1", 8000), allow_none=True, logRequests=False)
    server.register_introspection_functions()
    server.register_instance(PlannerComponent())
    print("="*50)
    print("COM-СЕРВЕР ЗАПУЩЕН")
    print("Слушаю порт: 8000")
    print("Ожидание запросов от клиента...")
    print("="*50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")

if __name__ == "__main__":
    start_com_server()