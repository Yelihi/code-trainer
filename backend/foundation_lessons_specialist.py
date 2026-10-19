"""Original specialist algorithms, with deterministic TypeScript references and tests."""
from .foundation_lessons_patterns import guide, scenes
from .foundation_lessons_advanced import graph_scene


def segment_scene(values, active, note, detail, code):
    points = [('all',275,20),('left',125,115),('right',425,115),
              ('v0',25,225),('v1',160,225),('v2',330,225),('v3',500,225)]
    edges = [('all','left'),('all','right'),('left','v0'),('left','v1'),('right','v2'),('right','v3')]
    result = graph_scene(points, edges, active, note, detail, code)
    labels = {'all':sum(values), 'left':sum(values[:2]), 'right':sum(values[2:]),
              **{f'v{i}':value for i,value in enumerate(values)}}
    intervals = {'all':'[0,4)', 'left':'[0,2)', 'right':'[2,4)',
                 **{f'v{i}':f'[{i},{i+1})' for i in range(4)}}
    for node in result['nodes']:
        node['label'] = str(labels[node['id']])
        node['annotation'] = intervals[node['id']]
    return result


def fenwick_scene(values, active, note, detail, code):
    points = [('i1',35,170),('i2',205,85),('i3',345,170),('i4',505,35)]
    result = graph_scene(points, [('i1','i2'),('i2','i4'),('i3','i4')], active, note, detail, code)
    labels = {'i1':values[0], 'i2':sum(values[:2]), 'i3':values[2], 'i4':sum(values)}
    intervals = {'i1':'[0,1)', 'i2':'[0,2)', 'i3':'[2,3)', 'i4':'[0,4)'}
    for node in result['nodes']:
        node['label'] = str(labels[node['id']])
        node['annotation'] = intervals[node['id']]
    return result


SPECIALIST_LESSONS = [
    dict(
        id='scc', title='강한 연결 요소 · 서로 도달하는 묶음', group='알고리즘', priority=3, difficulty='어려움',
        summary='방향 그래프에서 서로 오갈 수 있는 정점들을 묶습니다.',
        concept='강한 연결 요소는 묶음 안의 모든 정점 쌍이 서로 도달할 수 있는 최대 집합입니다. Kosaraju는 원래 그래프의 DFS 종료 순서를 기록한 뒤 간선을 뒤집고 종료 순서의 역순으로 DFS합니다. 두 번째 탐색에서 만난 정점이 한 요소입니다. 이 단원은 출력 비교를 위해 각 요소와 요소 목록을 정렬합니다.',
        complexity='정점·간선을 두 번 순회해 시간 O(V+E), 역방향 그래프·방문 기록·호출 스택에 공간 O(V+E).',
        application='서비스 의존 그래프에서 서로 순환 의존하는 모듈을 하나의 묶음으로 파악할 수 있습니다.',
        questions=[('한 방향으로만 도달하면 같은 강한 연결 요소인가요?', '아니다. 두 방향 모두 경로가 있어야 한다.'),
                   ('왜 두 번째 탐색에서 간선을 뒤집나요?', '종료 순서 역순으로 시작할 때 다른 요소로 새어 나가지 않고 현재 서로 도달하는 묶음을 모으기 위해서다.')],
        requirements=['`stronglyConnected(graph: number[][]): number[][]`를 구현하세요. 정점은 0부터 n-1입니다.',
                      '방향 간선·순환·자기 간선을 허용합니다. 각 요소 내부를 오름차순 정렬하고 요소 목록도 첫 원소순 정렬하세요.'],
        starter='function stronglyConnected(graph:number[][]):number[][] { return []; }',
        reference='''function stronglyConnected(graph:number[][]):number[][] {
  const n=graph.length, seen=Array(n).fill(false) as boolean[], order:number[]=[];
  function first(v:number):void {
    seen[v]=true;
    for (const next of graph[v]) if (!seen[next]) first(next);
    order.push(v);
  }
  for (let v=0;v<n;v++) if (!seen[v]) first(v);
  const reversed:number[][]=Array.from({length:n},()=>[]);
  for (let from=0;from<n;from++) for (const to of graph[from]) reversed[to].push(from);
  seen.fill(false); const result:number[][]=[];
  function second(v:number,group:number[]):void {
    seen[v]=true; group.push(v);
    for (const next of reversed[v]) if (!seen[next]) second(next,group);
  }
  for (let i=order.length-1;i>=0;i--) {
    const v=order[i]; if (seen[v]) continue;
    const group:number[]=[]; second(v,group); group.sort((a,b)=>a-b); result.push(group);
  }
  return result.sort((a,b)=>a[0]-b[0]);
}''',
        public_tests='assertEqual(stronglyConnected([[1],[0,2],[]]),[[0,1],[2]]); assertEqual(stronglyConnected([]),[]);',
        hidden_tests='''assertEqual(stronglyConnected([[1],[2],[0,3],[4],[3],[]]),[[0,1,2],[3,4],[5]]);
assertEqual(stronglyConnected([[0],[]]),[[0],[1]]);
assertEqual(stronglyConnected([[1],[]]),[[0],[1]]);''',
        mutations=[('역방향 간선', 'reversed[to].push(from);', 'reversed[from].push(to);'),
                   ('종료 역순', 'let i=order.length-1;i>=0;i--', 'let i=0;i<order.length;i++')],
        visualization='scc', visual_round=True, prerequisites=['dfs','adjacency-list'],
        reading=guide('두 번째 탐색의 한 번의 DFS는 역방향 그래프에서 한 강한 연결 요소에 머뭅니다.',
            [['종료 순서를 기록','원래 그래프에서 끝까지 간 뒤 돌아오며 정점을 기록합니다.'],['간선을 뒤집기','A↔B는 그대로 서로 연결되지만 B→C는 C→B가 됩니다.'],['역순으로 묶기','종료 순서 역순으로 DFS하면 서로 오갈 수 있는 A,B를 한 묶음으로 모읍니다.']],
            '단순한 연결 성분과 달리 방향을 따져야 합니다. A→B만으로는 같은 요소가 아닙니다.',
            '두 번의 전체 탐색으로 O(V+E)에 구합니다.',
            '모듈 의존 관계에서 순환적으로 서로 묶인 부분을 찾습니다.',
            'A↔B, B→C 그래프에서 C가 왜 따로인지 확인하세요.'),
        hints=['서로 왕복 가능한 두 정점에서 바깥으로 한 방향 간선만 추가하세요.', '고립 정점과 자기 간선이 있는 정점도 빠뜨리지 마세요.'],
        visual_frames=[graph_scene([('A',55,125),('B',245,125),('C',465,125)],[('A','B'),('B','A'),('B','C')],('A','B'),'A와 B는 서로 오갈 수 있습니다.','B에서 C로 갈 수 있어도 C에서 돌아올 수는 없습니다.','A↔B; B→C'),
                       graph_scene([('A',55,125),('B',245,125),('C',465,125)],[('B','A'),('A','B'),('C','B')],('C',),'간선 방향을 뒤집습니다.','종료 순서 역순으로 시작할 준비를 합니다.','reverse edges'),
                       graph_scene([('A',55,125),('B',245,125),('C',465,125)],[('B','A'),('A','B'),('C','B')],('A','B'),'A,B가 하나의 요소가 됩니다.','C는 돌아갈 경로가 없어 별도 요소입니다.','[[A,B],[C]]')]),
    dict(
        id='bridges', title='단절선 · 끊으면 갈라지는 간선', group='알고리즘', priority=3, difficulty='어려움',
        summary='무방향 그래프에서 한 간선을 제거하면 연결이 끊기는 경우를 찾습니다.',
        concept='DFS 진입 시각 tin과, 현재 부분 트리가 역방향 간선을 통해 도달할 수 있는 가장 이른 시각 low를 기록합니다. 자식의 low가 부모의 tin보다 크면 그 간선을 제거했을 때 자식 부분이 떨어져 단절선입니다. 평행 간선은 간선 ID를 따로 둬서 부모로 돌아가는 DFS 간선 하나만 건너뛰어야 합니다.',
        complexity='정점·간선을 한 번씩 살펴 시간 O(V+E), 인접 목록과 DFS 정보 공간 O(V+E). 결과 정렬 비용이 추가됩니다.',
        application='네트워크 케이블 하나가 끊어질 때 통신망이 둘로 나뉘는 취약 지점을 찾습니다.',
        questions=[('DFS 자식의 low가 부모 tin보다 크면 무엇을 뜻하나요?', '자식 부분 트리에서 부모나 더 이른 조상으로 돌아가는 경로가 없어 두 부분을 잇는 간선이 유일하다.'),
                   ('같은 두 정점을 잇는 평행 간선 둘은 왜 단절선이 아닌가요?', '하나를 제거해도 다른 간선으로 여전히 연결되기 때문이다.')],
        requirements=['`findBridges(vertexCount: number, edges: [number,number][]): [number,number][]`를 구현하세요.',
                      '무방향 그래프이며 평행·자기 간선을 허용합니다. 각 단절선은 작은 정점을 먼저 쓰고 결과는 사전식으로 정렬하세요.'],
        starter='function findBridges(vertexCount:number,edges:[number,number][]):[number,number][] { return []; }',
        reference='''function findBridges(vertexCount:number,edges:[number,number][]):[number,number][] {
  const graph:[number,number][][]=Array.from({length:vertexCount},()=>[]);
  edges.forEach(([a,b],id)=>{graph[a].push([b,id]);graph[b].push([a,id]);});
  const tin=Array(vertexCount).fill(-1) as number[], low=Array(vertexCount).fill(0) as number[];
  const result:[number,number][]=[]; let timer=0;
  function visit(v:number,parentEdge:number):void {
    tin[v]=low[v]=timer++;
    for (const [next,id] of graph[v]) {
      if (id===parentEdge) continue;
      if (tin[next]!==-1) { low[v]=Math.min(low[v],tin[next]); continue; }
      visit(next,id); low[v]=Math.min(low[v],low[next]);
      if (low[next]>tin[v]) result.push([Math.min(v,next),Math.max(v,next)]);
    }
  }
  for (let v=0;v<vertexCount;v++) if (tin[v]===-1) visit(v,-1);
  return result.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
}''',
        public_tests='assertEqual(findBridges(4,[[0,1],[1,2],[2,0],[1,3]]),[[1,3]]); assertEqual(findBridges(2,[[0,1],[0,1]]),[]);',
        hidden_tests='''assertEqual(findBridges(3,[[0,1],[1,2]]),[[0,1],[1,2]]);
assertEqual(findBridges(4,[[0,1],[1,2],[2,0],[2,3]]),[[2,3]]);
assertEqual(findBridges(2,[[0,0],[0,1],[0,1]]),[]);
assertEqual(findBridges(0,[]),[]);''',
        mutations=[('되돌아가는 경계', 'low[next]>tin[v]', 'low[next]>=tin[v]'),
                   ('조상 시각 전달', 'Math.min(low[v],low[next])', 'Math.min(low[v],tin[next])')],
        visualization='bridges', visual_round=True, prerequisites=['dfs','union-find'],
        reading=guide('low[v]는 v의 부분 트리에서 트리 간선과 역방향 간선을 이용해 닿는 가장 이른 DFS 시각입니다.',
            [['DFS 시각을 기록','방문할 때 순서 번호를 붙입니다.'],['되돌아갈 길을 확인','삼각형 안의 간선은 다른 경로로 우회할 수 있습니다.'],['유일한 연결을 표시','삼각형에서 바깥 정점으로 이어지는 한 간선만 단절선입니다.']],
            '평행 간선을 부모 정점만으로 건너뛰면 다른 평행 간선까지 놓칩니다. 간선 ID로 하나만 건너뛰어야 합니다.',
            '전체 탐색은 선형이며 반환 결과의 정렬이 추가됩니다.',
            '통신망에서 단일 케이블 장애가 분리를 일으키는지 확인합니다.',
            '삼각형에 꼬리 하나를 붙인 그래프와 평행 간선 두 개를 비교하세요.'),
        hints=['삼각형 내부의 간선은 단절선이 아닌지 확인하세요.', '같은 두 정점 사이에 평행 간선 두 개가 있으면 어느 것도 단절선이 아닙니다.'],
        visual_frames=[graph_scene([('0',70,75),('1',260,35),('2',260,225),('3',490,135)],[('0','1'),('1','2'),('2','0'),('1','3')],('0','1','2'),'삼각형에는 우회 경로가 있습니다.','내부 간선 하나를 끊어도 세 정점은 연결됩니다.'),
                       graph_scene([('0',70,75),('1',260,35),('2',260,225),('3',490,135)],[('0','1'),('1','2'),('2','0'),('1','3')],('1','3'),'1–3은 유일한 연결입니다.','3은 삼각형으로 돌아갈 다른 경로가 없습니다.','low[3] > tin[1]'),
                       graph_scene([('0',70,75),('1',260,35),('2',260,225),('3',490,135)],[('0','1'),('1','2'),('2','0'),('1','3')],('3',),'1–3을 제거하면 3이 분리됩니다.','단절선 결과는 [[1,3]]입니다.','return [[1,3]]')]),
    dict(
        id='articulation-points', title='단절점 · 빠지면 갈라지는 정점', group='알고리즘', priority=3, difficulty='어려움',
        summary='한 정점을 제거할 때 연결 성분 수가 늘어나는 지점을 찾습니다.',
        concept='DFS의 tin과 low를 이용합니다. 루트가 아닌 v의 자식 부분 트리가 v보다 이른 조상으로 돌아갈 수 없다면 v를 제거할 때 분리됩니다. 루트는 DFS 자식이 둘 이상일 때만 단절점입니다. 평행 간선은 간선 ID로 구분해 부모 트리 간선 한 개만 건너뜁니다.',
        complexity='탐색 시간 O(V+E), 자료 저장 공간 O(V+E). 결과를 정렬하는 비용이 더해집니다.',
        application='네트워크 중계 지점 한 개가 사라지면 연결이 끊기는 위험을 찾습니다.',
        questions=[('DFS 루트가 단절점이 되는 조건은 무엇인가요?', '서로 다른 DFS 자식이 둘 이상 있을 때다.'),
                   ('루트가 아닌 정점 v의 자식 low가 tin[v]와 같아도 v는 단절점인가요?', '그렇다. 그 자식 부분은 v까지는 돌아오지만 v를 거치지 않고 더 이른 조상으로는 갈 수 없다.')],
        requirements=['`articulationPoints(vertexCount: number, edges: [number,number][]): number[]`를 구현하세요.',
                      '무방향 그래프이며 평행·자기 간선을 허용합니다. 결과 정점을 오름차순으로 한 번씩 반환하세요.'],
        starter='function articulationPoints(vertexCount:number,edges:[number,number][]):number[] { return []; }',
        reference='''function articulationPoints(vertexCount:number,edges:[number,number][]):number[] {
  const graph:[number,number][][]=Array.from({length:vertexCount},()=>[]);
  edges.forEach(([a,b],id)=>{graph[a].push([b,id]);graph[b].push([a,id]);});
  const tin=Array(vertexCount).fill(-1) as number[], low=Array(vertexCount).fill(0) as number[];
  const cut=new Set<number>(); let timer=0;
  function visit(v:number,parentEdge:number):void {
    tin[v]=low[v]=timer++; let children=0;
    for (const [next,id] of graph[v]) {
      if (id===parentEdge) continue;
      if (tin[next]!==-1) { low[v]=Math.min(low[v],tin[next]); continue; }
      visit(next,id); children++; low[v]=Math.min(low[v],low[next]);
      if (parentEdge!==-1 && low[next]>=tin[v]) cut.add(v);
    }
    if (parentEdge===-1 && children>1) cut.add(v);
  }
  for (let v=0;v<vertexCount;v++) if (tin[v]===-1) visit(v,-1);
  return [...cut].sort((a,b)=>a-b);
}''',
        public_tests='assertEqual(articulationPoints(4,[[0,1],[1,2],[2,0],[1,3]]),[1]); assertEqual(articulationPoints(3,[[0,1],[1,2],[2,0]]),[]);',
        hidden_tests='''assertEqual(articulationPoints(3,[[0,1],[1,2]]),[1]);
assertEqual(articulationPoints(4,[[0,1],[1,2],[2,3],[3,1]]),[1]);
assertEqual(articulationPoints(4,[[0,1],[0,2],[0,3]]),[0]);
assertEqual(articulationPoints(2,[[0,1],[0,1]]),[]);
assertEqual(articulationPoints(0,[]),[]);''',
        mutations=[('루트 자식 수', 'children>1', 'children>=1'),
                   ('조상 경계', 'low[next]>=tin[v]', 'low[next]>tin[v]')],
        visualization='articulation-points', visual_round=True, prerequisites=['bridges'],
        reading=guide('자식 부분의 low는 해당 정점을 거치지 않고 연결될 수 있는 가장 이른 조상을 가리킵니다.',
            [['DFS 트리를 만든다','삼각형과 바깥 정점을 따라 탐색합니다.'],['자식의 우회 경로를 본다','삼각형 안의 정점은 돌아갈 경로가 있지만 바깥 정점은 다릅니다.'],['제거 후 분리를 판단','접점 1을 제거하면 바깥 정점 3이 분리됩니다.']],
            '루트에 다른 규칙이 필요합니다. 자식이 한 개뿐인 DFS 루트를 단절점으로 판정하면 안 됩니다.',
            '전체 DFS는 선형이며 결과 정렬이 더해집니다.',
            '중계 서버 한 대가 빠질 때 네트워크가 둘로 나뉘는지 판단합니다.',
            '삼각형 내부 정점과 꼬리 연결 지점을 제거해 보세요.'),
        hints=['루트에 DFS 자식이 하나뿐인 선형 그래프를 확인하세요.', '삼각형에 꼬리가 달린 그래프에서 접점만 나오는지 확인하세요.'],
        visual_frames=[graph_scene([('0',70,75),('1',260,35),('2',260,225),('3',490,135)],[('0','1'),('1','2'),('2','0'),('1','3')],('1',),'정점 1이 두 부분을 잇습니다.','삼각형과 바깥 정점 3의 접점입니다.'),
                       graph_scene([('0',70,75),('1',260,35),('2',260,225),('3',490,135)],[('0','1'),('1','2'),('2','0')],('3',),'1을 제거한 상태를 생각합니다.','3은 나머지 삼각형으로 갈 수 없습니다.','cut.add(1)'),
                       graph_scene([('0',70,75),('1',260,35),('2',260,225),('3',490,135)],[('0','1'),('1','2'),('2','0')],('1',),'단절점은 1입니다.','0과 2는 서로 우회 경로가 있어 단절점이 아닙니다.','return [1]')]),
    dict(
        id='max-flow', title='최대 유량 · 남은 용량으로 증대하기', group='알고리즘', priority=3, difficulty='어려움',
        summary='방향 간선의 용량을 지키며 출발점에서 도착점까지 보낼 수 있는 최대량을 구합니다.',
        concept='잔여 그래프는 앞으로 더 보낼 수 있는 용량과 이미 보낸 유량을 되돌릴 수 있는 역방향 용량을 기록합니다. Edmonds–Karp는 BFS로 잔여 용량이 있는 증대 경로를 찾고, 그 경로에서 가장 작은 용량만큼 유량을 보냅니다. 역방향 간선은 앞선 선택을 재배치할 수 있게 합니다. 더 이상 경로가 없으면 유량이 최대입니다.',
        complexity='BFS 증대 경로를 반복해 시간 O(VE²), 잔여 용량 행렬을 쓰면 공간 O(V²).',
        application='서버 사이 전송 한도가 주어졌을 때 네트워크가 동시에 전달할 수 있는 최대 요청량을 계산합니다.',
        questions=[('잔여 그래프의 역방향 용량은 무엇을 뜻하나요?', '이미 보낸 유량 일부를 취소하고 다른 경로로 재배치할 수 있는 양이다.'),
                   ('증대 경로에서 왜 가장 작은 용량만큼만 보내나요?', '한 간선이라도 용량을 넘기면 유효한 흐름이 아니기 때문이다.')],
        requirements=['`maxFlow(vertexCount: number, edges: [number,number,number][], source: number, sink: number): number`를 구현하세요.',
                      '방향 간선·평행 간선과 0 용량을 허용합니다. source와 sink가 같으면 0을 반환합니다.'],
        starter='function maxFlow(vertexCount:number,edges:[number,number,number][],source:number,sink:number):number { return 0; }',
        reference='''function maxFlow(vertexCount:number,edges:[number,number,number][],source:number,sink:number):number {
  if (source===sink) return 0;
  const capacity:number[][]=Array.from({length:vertexCount},()=>Array(vertexCount).fill(0));
  const neighbors:number[][]=Array.from({length:vertexCount},()=>[]);
  for (const [from,to,amount] of edges) {
    capacity[from][to]+=amount;
    neighbors[from].push(to); neighbors[to].push(from);
  }
  let total=0;
  while (true) {
    const parent=Array(vertexCount).fill(-1) as number[], queue=[source]; parent[source]=source;
    for (let head=0;head<queue.length && parent[sink]===-1;head++) {
      const from=queue[head];
      for (const to of neighbors[from]) if (parent[to]===-1 && capacity[from][to]>0) {
        parent[to]=from; queue.push(to);
      }
    }
    if (parent[sink]===-1) return total;
    let amount=Infinity;
    for (let v=sink;v!==source;v=parent[v]) amount=Math.min(amount,capacity[parent[v]][v]);
    for (let v=sink;v!==source;v=parent[v]) {
      capacity[parent[v]][v]-=amount; capacity[v][parent[v]]+=amount;
    }
    total+=amount;
  }
}''',
        public_tests='assertEqual(maxFlow(4,[[0,1,3],[0,2,2],[1,2,1],[1,3,2],[2,3,3]],0,3),5); assertEqual(maxFlow(2,[[0,1,2],[0,1,3]],0,1),5);',
        hidden_tests='''assertEqual(maxFlow(4,[[0,1,1],[0,2,1],[1,2,1],[1,3,1],[2,3,1]],0,3),2);
assertEqual(maxFlow(3,[[0,1,0],[1,2,4]],0,2),0);
assertEqual(maxFlow(2,[[0,1,5]],0,0),0);
assertEqual(maxFlow(3,[[0,1,2],[1,2,5]],0,2),2);
assertEqual(maxFlow(3,[[0,1,5],[1,2,2]],0,2),2);
assertEqual(maxFlow(4,[[0,1,1],[0,2,1],[1,3,1],[2,3,1],[1,2,1]],0,3),2);''',
        mutations=[('평행 간선 용량', 'capacity[from][to]+=amount;', 'capacity[from][to]=amount;'),
                   ('경로 병목', 'amount=Math.min(amount,capacity[parent[v]][v])', 'amount=capacity[parent[v]][v]')],
        visualization='max-flow', visual_round=True, prerequisites=['bfs-distances','adjacency-list'],
        sources=[{'title':'MIT 6.046J · 최대 유량 강의 노트', 'url':'https://ocw.mit.edu/courses/6-046j-design-and-analysis-of-algorithms-spring-2015/ac6b6e8ac932bb5dfb6506fd0db9d5ad_MIT6_046JS15_lec13.pdf'}],
        reading=guide('잔여 간선의 양수 용량만 따라가며, 보낸 양은 정방향에서 빼고 역방향에 더합니다.',
            [['경로 찾기','남은 용량이 있는 간선만 BFS로 따라갑니다.'],['병목 찾기','경로의 용량 중 최솟값만큼 보낼 수 있습니다.'],['잔여 용량 갱신','정방향을 줄이고 역방향을 늘려 다음 경로를 찾습니다.']],
            '처음 고른 경로가 최선일 필요는 없습니다. 역방향 잔여 간선으로 그 선택을 바꿀 수 있어야 합니다.',
            'Edmonds–Karp는 증대 경로 BFS를 반복해 O(VE²)입니다.',
            '네트워크 링크 용량에서 동시에 보낼 수 있는 최대량을 구합니다.',
            '두 경로가 가운데 간선을 공유할 때 역방향 용량이 왜 필요한지 살펴보세요.'),
        hints=['평행 간선의 용량을 합산해야 합니다.', '경로 전체가 가장 작은 용량을 넘지 않는지 확인하세요.'],
        visual_frames=[graph_scene([('S',45,130),('A',220,45),('B',220,215),('T',455,130)],[('S','A'),('S','B'),('A','B'),('A','T'),('B','T')],('S','A','T'),'S→A→T 경로를 찾습니다.','A→T 용량 2가 병목입니다.','send 2'),
                       graph_scene([('S',45,130),('A',220,45),('B',220,215),('T',455,130)],[('S','A'),('S','B'),('A','B'),('A','T'),('B','T')],('S','B','T'),'S→B→T로 2를 더 보냅니다.','남은 용량은 잔여 그래프에 기록됩니다.','total 4'),
                       graph_scene([('S',45,130),('A',220,45),('B',220,215),('T',455,130)],[('S','A'),('S','B'),('A','B'),('A','T'),('B','T')],('A','B'),'남은 경로에 1을 더 보냅니다.','더 이상 증대 경로가 없으면 최대 유량 5입니다.','total 5')]),
    dict(
        id='bipartite-matching', title='이분 매칭 · 짝을 다시 배치하기', group='알고리즘', priority=3, difficulty='어려움',
        summary='두 집합 사이에서 정점마다 하나씩만 연결하는 최대 짝 수를 찾습니다.',
        concept='이분 그래프의 왼쪽 정점을 차례로 보며 오른쪽 후보를 찾습니다. 후보가 이미 매칭되었다면 기존 왼쪽 정점이 다른 후보로 옮길 수 있는지 재귀적으로 시도합니다. 이 증대 경로가 있으면 매칭 수가 하나 늘어납니다. 한 번의 시도에서 같은 오른쪽 정점을 반복 방문하지 않습니다.',
        complexity='각 왼쪽 정점에서 간선을 탐색하는 기본 증대 경로 구현은 시간 O(L·E), 매칭·방문 기록에 공간 O(L+R+E).',
        application='지원 가능한 근무자와 시간대가 주어졌을 때 배정할 수 있는 최대 근무자 수를 찾습니다.',
        questions=[('이미 매칭된 오른쪽 정점을 다시 살피는 이유는 무엇인가요?', '기존 짝을 다른 자리로 옮기면 현재 왼쪽 정점도 배정할 수 있기 때문이다.'),
                   ('방문 표시를 왼쪽 정점마다 새로 만드는 이유는 무엇인가요?', '증대 경로의 한 번의 탐색 안에서만 중복을 막고 다음 정점에서는 같은 오른쪽 후보를 다시 고려해야 하기 때문이다.')],
        requirements=['`maximumMatching(leftCount: number, rightCount: number, edges: [number,number][]): number`를 구현하세요.',
                      '간선은 왼쪽·오른쪽 인덱스 쌍입니다. 중복 간선·고립 정점을 허용하며 최대 매칭 크기를 반환하세요.'],
        starter='function maximumMatching(leftCount:number,rightCount:number,edges:[number,number][]):number { return 0; }',
        reference='''function maximumMatching(leftCount:number,rightCount:number,edges:[number,number][]):number {
  const graph:number[][]=Array.from({length:leftCount},()=>[]);
  for (const [left,right] of edges) graph[left].push(right);
  const match=Array(rightCount).fill(-1) as number[];
  function visit(left:number,seen:Set<number>):boolean {
    for (const right of graph[left]) {
      if (seen.has(right)) continue;
      seen.add(right);
      if (match[right]===-1 || visit(match[right],seen)) { match[right]=left; return true; }
    }
    return false;
  }
  let count=0;
  for (let left=0;left<leftCount;left++) if (visit(left,new Set<number>())) count++;
  return count;
}''',
        public_tests='assertEqual(maximumMatching(2,2,[[0,0],[0,1],[1,0]]),2); assertEqual(maximumMatching(2,1,[[0,0],[1,0]]),1);',
        hidden_tests='''assertEqual(maximumMatching(0,2,[]),0);
assertEqual(maximumMatching(3,3,[[0,0],[1,0],[1,1],[2,1],[2,2]]),3);
assertEqual(maximumMatching(2,2,[[0,0],[0,0],[1,1]]),2);
assertEqual(maximumMatching(3,2,[[0,1],[1,0],[2,1]]),2);''',
        mutations=[('이미 잡힌 짝 재배치', 'match[right]===-1 || visit(match[right],seen)', 'match[right]===-1'),
                   ('마지막 왼쪽 정점', 'left<leftCount;left++', 'left<leftCount-1;left++')],
        visualization='bipartite-matching', visual_round=True, prerequisites=['max-flow'],
        sources=[{'title':'MIT 6.1200J · 매칭 강의 노트', 'url':'https://ocw.mit.edu/courses/6-1200j-mathematics-for-computer-science-spring-2024/resources/mit6_1200j_s24_lec12_pdf/'}],
        reading=guide('증대 경로를 찾으면 기존 짝을 하나씩 옮겨 전체 매칭 수를 정확히 하나 늘립니다.',
            [['첫 짝 만들기','왼쪽 A가 오른쪽 1을 선택합니다.'],['충돌 살피기','왼쪽 B도 1을 원하지만 A를 2로 옮길 수 있습니다.'],['짝 재배치','A→2, B→1로 두 정점 모두 배정됩니다.']],
            '탐욕적으로 빈 후보만 보면 가능한 재배치를 놓칩니다.',
            '기본 증대 경로 구현의 시간은 O(L·E)입니다.',
            '근무자와 가능한 근무 시간을 최대한 많이 연결합니다.',
            'A가 1과 2에, B가 1에 연결될 때 A를 2로 옮겨 보세요.'),
        hints=['첫 번째 왼쪽 정점이 선택한 후보를 다른 후보로 옮겨야 하는 경우를 만드세요.', '오른쪽 정점 하나를 두 왼쪽 정점이 공유하면 둘 다 배정되지는 않습니다.'],
        visual_frames=[graph_scene([('A',65,75),('B',65,215),('1',435,75),('2',435,215)],[('A','1'),('A','2'),('B','1')],('A','1'),'A가 1을 먼저 선택합니다.','B도 1만 선택할 수 있어 충돌합니다.','A→1'),
                       graph_scene([('A',65,75),('B',65,215),('1',435,75),('2',435,215)],[('A','1'),('A','2'),('B','1')],('A','2'),'A를 2로 옮깁니다.','이전 매칭을 재배치할 수 있습니다.','A→2'),
                       graph_scene([('A',65,75),('B',65,215),('1',435,75),('2',435,215)],[('A','1'),('A','2'),('B','1')],('B','1'),'B가 1을 차지합니다.','최대 매칭 크기는 2입니다.','return 2')]),
    dict(
        id='segment-tree', title='세그먼트 트리 · 구간 합 갱신하기', group='자료구조', priority=3, difficulty='어려움',
        summary='부분 구간의 합을 유지하면서 한 위치의 값을 바꿉니다.',
        concept='세그먼트 트리의 각 노드는 하나의 연속 구간 합을 저장합니다. 부모 구간은 왼쪽·오른쪽 절반으로 나뉘고 부모 합은 두 자식 합입니다. 한 값이 바뀌면 그 위치를 포함하는 노드만 루트까지 다시 계산합니다. 질의 구간과 겹치지 않으면 0, 완전히 포함되면 저장된 합을 반환합니다.',
        complexity='트리 생성 O(n), 점 갱신·구간 합 질의 O(log n), 저장 공간 O(n).',
        application='매 시간 달라지는 판매량에서 임의 기간의 합계를 빠르게 조회합니다.',
        questions=[('한 값이 바뀔 때 왜 모든 노드를 다시 계산하지 않아도 되나요?', '그 값을 포함하는 구간의 조상 노드만 합이 달라지기 때문이다.'),
                   ('질의 구간과 노드 구간이 완전히 겹치면 어떻게 하나요?', '그 노드에 저장된 합을 그대로 사용하고 아래로 더 내려가지 않는다.')],
        requirements=['`SegmentTree`의 생성자는 숫자 배열을 받습니다. `update(index,value): void`, `rangeSum(left,right): number`를 구현하세요.',
                      '구간은 반열린 [left,right)이며 빈 배열·빈 구간의 합은 0입니다. 유효한 인덱스만 입력됩니다.'],
        starter='class SegmentTree { constructor(values:number[]) {} update(index:number,value:number):void {} rangeSum(left:number,right:number):number { return 0; } }',
        reference='''class SegmentTree {
  private tree:number[];
  private n:number;
  constructor(values:number[]) {
    this.n=values.length; this.tree=Array(Math.max(1,4*this.n)).fill(0);
    const build=(node:number,left:number,right:number):void=>{
      if (right-left===1) { this.tree[node]=values[left]; return; }
      const mid=Math.floor((left+right)/2);
      build(node*2,left,mid); build(node*2+1,mid,right);
      this.tree[node]=this.tree[node*2]+this.tree[node*2+1];
    };
    if (this.n) build(1,0,this.n);
  }
  update(index:number,value:number):void {
    const change=(node:number,left:number,right:number):void=>{
      if (right-left===1) { this.tree[node]=value; return; }
      const mid=Math.floor((left+right)/2);
      if (index<mid) change(node*2,left,mid); else change(node*2+1,mid,right);
      this.tree[node]=this.tree[node*2]+this.tree[node*2+1];
    };
    change(1,0,this.n);
  }
  rangeSum(left:number,right:number):number {
    const sum=(node:number,start:number,end:number):number=>{
      if (right<=start || end<=left) return 0;
      if (left<=start && end<=right) return this.tree[node];
      const mid=Math.floor((start+end)/2);
      return sum(node*2,start,mid)+sum(node*2+1,mid,end);
    };
    return this.n ? sum(1,0,this.n) : 0;
  }
}''',
        public_tests='const tree=new SegmentTree([2,1,3,4]); assertEqual(tree.rangeSum(1,3),4); tree.update(2,8); assertEqual(tree.rangeSum(0,4),15);',
        hidden_tests='''const tree=new SegmentTree([]); assertEqual(tree.rangeSum(0,0),0);
const other=new SegmentTree([-2,0,5,1,7]); assertEqual(other.rangeSum(2,2),0); assertEqual(other.rangeSum(3,5),8);
other.update(4,-3); assertEqual(other.rangeSum(0,5),1); assertEqual(other.rangeSum(4,5),-3);
other.update(0,10); assertEqual(other.rangeSum(0,1),10);''',
        mutations=[('갱신 후 부모 합', 'this.tree[node]=this.tree[node*2]+this.tree[node*2+1];', 'this.tree[node]=this.tree[node*2];'),
                   ('왼쪽 경계 하나 제외', 'end<=left', 'end<=left+1')],
        visualization='segment-tree', prerequisites=['tree-inorder','prefix-sums'],
        sources=[{'title':'USACO Guide · 점 갱신과 구간 합', 'url':'https://usaco.guide/gold/PURS'}],
        reading=guide('부모의 합은 두 자식 합이며, [left,right) 구간 규칙을 생성·갱신·질의에 공통 적용합니다.',
            [['배열을 구간으로 나누기','[0,4)를 [0,2)와 [2,4)로 나눕니다.'],['구간 합 저장','부모에는 자식 두 구간의 합을 저장합니다.'],['한 값 갱신','바뀐 잎에서 루트까지의 합만 다시 계산합니다.']],
            '경계가 포함되는지 혼동하면 빈 구간이나 마지막 원소 질의가 잘못됩니다.',
            '생성 O(n), 갱신과 질의 O(log n)입니다.',
            '수정되는 날짜별 판매량에서 기간 합계를 조회합니다.',
            '[2,1,3,4]에서 세 번째 값을 8로 바꾼 뒤 전체 합을 보세요.'),
        hints=['가운데 원소를 바꾼 뒤 전체 구간과 그 원소만 질의하세요.', '빈 구간과 마지막 원소 하나만 포함한 구간을 확인하세요.'],
        visual_frames=[segment_scene([2,1,3,4],('left','right'),'두 자식 구간의 합을 저장합니다.','[0,2)의 합은 3이고 [2,4)의 합은 7입니다.','3 + 7 = 10'),
                       segment_scene([2,1,3,4],('v2',),'세 번째 값 3을 8로 바꿉니다.','[2,3) 잎에서 부모 방향으로 합을 다시 계산합니다.','update(2, 8)'),
                       segment_scene([2,1,8,4],('v2','right','all'),'관련 조상 구간의 합이 바뀝니다.','[2,4)는 12, 전체 [0,4)는 15가 됩니다.','12 + 3 = 15')]),
    dict(
        id='fenwick-tree', title='펜윅 트리 · 접두 합 누적하기', group='자료구조', priority=3, difficulty='어려움',
        summary='한 값에 변화량을 더하고 접두 구간의 합을 빠르게 구합니다.',
        concept='펜윅 트리의 1부터 시작하는 인덱스 i는 끝이 i인 길이 i&-i의 구간 합을 저장합니다. add는 i에 변화량을 더하고 i += i&-i로 관련 상위 구간을 갱신합니다. prefixSum은 i -= i&-i로 겹치지 않는 저장 구간들을 더합니다. 임의 반열린 구간은 두 접두 합의 차이입니다.',
        complexity='생성 O(n log n), add·prefixSum·rangeSum O(log n), 공간 O(n).',
        application='실시간 조회수가 더해질 때 앞선 날짜까지의 누적 조회수와 임의 기간 합계를 계산합니다.',
        questions=[('인덱스를 1부터 시작하는 이유는 무엇인가요?', '최하위 켜진 비트 i&-i를 이용해 저장 구간 길이와 다음 인덱스를 계산하기 쉽기 때문이다.'),
                   ('[left,right) 합을 어떻게 구하나요?', 'prefixSum(right)에서 prefixSum(left)를 뺀다.')],
        requirements=['`FenwickTree`의 생성자는 숫자 배열을 받습니다. `add(index,delta): void`, `prefixSum(end): number`, `rangeSum(left,right): number`를 구현하세요.',
                      'end는 앞에서부터 포함할 원소 수, 구간은 [left,right)입니다. 유효한 인덱스만 입력됩니다.'],
        starter='class FenwickTree { constructor(values:number[]) {} add(index:number,delta:number):void {} prefixSum(end:number):number { return 0; } rangeSum(left:number,right:number):number { return 0; } }',
        reference='''class FenwickTree {
  private tree:number[];
  constructor(values:number[]) {
    this.tree=Array(values.length+1).fill(0);
    values.forEach((value,index)=>this.add(index,value));
  }
  add(index:number,delta:number):void {
    for (let i=index+1;i<this.tree.length;i+=i&-i) this.tree[i]+=delta;
  }
  prefixSum(end:number):number {
    let result=0;
    for (let i=end;i>0;i-=i&-i) result+=this.tree[i];
    return result;
  }
  rangeSum(left:number,right:number):number { return this.prefixSum(right)-this.prefixSum(left); }
}''',
        public_tests='const tree=new FenwickTree([2,1,3,4]); assertEqual(tree.prefixSum(3),6); tree.add(1,5); assertEqual(tree.rangeSum(1,4),13);',
        hidden_tests='''const tree=new FenwickTree([]); assertEqual(tree.prefixSum(0),0); assertEqual(tree.rangeSum(0,0),0);
const other=new FenwickTree([-2,0,5,1,7]); assertEqual(other.rangeSum(2,5),13);
other.add(4,-10); assertEqual(other.prefixSum(5),1); assertEqual(other.rangeSum(4,5),-3);
other.add(0,12); assertEqual(other.rangeSum(0,1),10);''',
        mutations=[('상위 구간 갱신', 'i+=i&-i', 'i+=1'),
                   ('반열린 구간 차이', 'this.prefixSum(right)-this.prefixSum(left)', 'this.prefixSum(right)-this.prefixSum(left+1)')],
        visualization='fenwick-tree', prerequisites=['prefix-sums','segment-tree'],
        sources=[{'title':'USACO Guide · 점 갱신과 구간 합', 'url':'https://usaco.guide/gold/PURS'}],
        reading=guide('tree[i]는 i에서 끝나는 길이 i&-i의 구간 합이며 질의는 겹치지 않는 저장 구간의 합입니다.',
            [['1부터 번호 매기기','배열 위치 0은 내부 인덱스 1에 대응합니다.'],['상위 구간 갱신','낮은 비트를 더해 해당 값을 포함하는 다음 구간으로 갑니다.'],['접두 합 모으기','낮은 비트를 빼며 겹치지 않는 구간을 합칩니다.']],
            '0 기반 배열 위치와 1 기반 내부 인덱스를 섞으면 첫 원소나 마지막 원소를 놓칩니다.',
            '변화량 추가와 구간 합 질의가 모두 O(log n)입니다.',
            '늘어나는 일별 이벤트 수에서 누적 합계를 조회합니다.',
            '[2,1,3,4]의 두 번째 원소에 5를 더하고 [1,4)를 더해 보세요.'),
        hints=['첫 원소와 마지막 원소를 각각 갱신해 보세요.', '빈 구간의 합과 앞에서 end개 원소의 합을 확인하세요.'],
        visual_frames=[fenwick_scene([2,1,3,4],('i3','i2'),'접두 합을 저장 구간 둘로 모읍니다.','앞의 세 값은 [0,2)와 [2,3)을 합쳐 3 + 3 = 6입니다.','prefixSum(3)=6'),
                       fenwick_scene([2,1,3,4],('i2','i4'),'두 번째 값에 5를 더합니다.','[0,2)와 [0,4)를 저장하는 내부 인덱스 2, 4만 갱신합니다.','2 → 4'),
                       fenwick_scene([2,6,3,4],('i2','i4'),'내부 구간 합을 다시 확인합니다.','[0,4)는 15이고 [1,4)는 15 - [0,1)의 합 2 = 13입니다.','15 - 2 = 13')]),
    dict(
        id='kmp', title='KMP · 앞에서 본 접두사 재사용하기', group='알고리즘', priority=3, difficulty='어려움',
        summary='문자열에서 패턴의 모든 등장 위치를 선형 시간에 찾습니다.',
        concept='패턴의 prefix 배열은 각 위치까지의 문자열에서 접두사이면서 접미사인 가장 긴 진부분 문자열의 길이를 저장합니다. 검색 중 불일치하면 이미 맞춘 문자를 처음부터 다시 비교하지 않고 prefix 값을 이용해 가능한 가장 긴 접두사로 돌아갑니다. 일치 뒤에도 같은 방식으로 이동해 겹치는 등장 위치를 놓치지 않습니다.',
        complexity='패턴 전처리 O(m), 본문 검색 O(n), prefix 배열과 결과에 공간 O(m+k).',
        application='긴 로그에서 오류 코드 문자열이 나타나는 모든 위치를 찾습니다.',
        questions=[('불일치할 때 이미 일치한 문자를 모두 버리지 않는 이유는 무엇인가요?', '일치 부분의 접미사가 패턴 접두사와 같다면 그 부분을 재사용할 수 있기 때문이다.'),
                   ('하나를 찾은 뒤 prefix 값으로 돌아가는 이유는 무엇인가요?', '패턴이 자기 자신과 겹쳐 다시 시작하는 등장도 찾기 위해서다.')],
        requirements=['`findPattern(text: string, pattern: string): number[]`를 구현하세요. 등장 시작 인덱스를 오름차순 반환합니다.',
                      '겹치는 등장도 포함합니다. 빈 패턴은 0부터 text.length까지 모든 경계 위치와 일치합니다. 인덱스 단위는 JavaScript 문자열 코드 단위입니다.'],
        starter='function findPattern(text:string,pattern:string):number[] { return []; }',
        reference='''function findPattern(text:string,pattern:string):number[] {
  if (!pattern.length) return Array.from({length:text.length+1},(_,i)=>i);
  const prefix=Array(pattern.length).fill(0) as number[];
  for (let i=1,j=0;i<pattern.length;i++) {
    while (j>0 && pattern[i]!==pattern[j]) j=prefix[j-1];
    if (pattern[i]===pattern[j]) j++;
    prefix[i]=j;
  }
  const result:number[]=[];
  for (let i=0,j=0;i<text.length;i++) {
    while (j>0 && text[i]!==pattern[j]) j=prefix[j-1];
    if (text[i]===pattern[j]) j++;
    if (j===pattern.length) { result.push(i-j+1); j=prefix[j-1]; }
  }
  return result;
}''',
        public_tests='assertEqual(findPattern("ababa","aba"),[0,2]); assertEqual(findPattern("aaaa","aa"),[0,1,2]);',
        hidden_tests='''assertEqual(findPattern("abc", ""),[0,1,2,3]);
assertEqual(findPattern("", "a"),[]);
assertEqual(findPattern("abababacababac", "ababac"),[2,8]);
assertEqual(findPattern("abcabc", "bc"),[1,4]);''',
        mutations=[('겹치는 일치', 'result.push(i-j+1); j=prefix[j-1];', 'result.push(i-j+1); j=0;'),
                   ('불일치 접두사 재사용', 'j=prefix[j-1];', 'j=0;')],
        visualization='kmp', prerequisites=['string-codepoints','sliding-window-sum'],
        sources=[{'title':'MIT 18.417 · 문자열 검색 강의 노트', 'url':'https://ocw.mit.edu/courses/18-417-introduction-to-computational-molecular-biology-fall-2004/f4800301e44750bc2bd5d4fb53f3f8de_lecture_10.pdf'}],
        reading=guide('prefix[i]는 pattern[0..i]의 양 끝에서 같은 가장 긴 진부분 문자열의 길이입니다.',
            [['패턴 경계 계산','aba의 앞 a와 뒤 a가 이어질 수 있음을 기록합니다.'],['본문을 왼쪽부터 읽기','ababa에서 처음 aba를 찾습니다.'],['겹치는 부분 재사용','뒤의 a를 새 시작으로 삼아 위치 2의 aba도 찾습니다.']],
            '완전 일치 후 인덱스를 0으로 되돌리면 겹치는 결과를 놓칩니다.',
            '본문 n, 패턴 m에 O(n+m)으로 탐색합니다.',
            '로그 파일에서 반복되는 오류 문자열 위치를 찾습니다.',
            'ababa에서 aba가 0과 2에 있는 이유를 따라가 보세요.'),
        hints=['aaaa에서 aa를 찾으면 겹치는 시작 위치가 세 개입니다.', '불일치 전에 맞춘 접두사가 다음 시도에 재사용될 수 있습니다.'],
        visual_frames=scenes((['a','b','a'],[0,2],'패턴 aba의 양 끝이 같습니다.','마지막 a는 다음 일치의 시작이 될 수 있습니다.','prefix=[0,0,1]'),
                              (['a','b','a','b','a'],[0,1,2],'본문의 처음 aba를 찾습니다.','위치 0에서 완전 일치합니다.','found 0'),
                              (['a','b','a','b','a'],[2,3,4],'겹친 a부터 다시 비교합니다.','위치 2에서도 aba가 나타납니다.','found [0,2]'))),
]
