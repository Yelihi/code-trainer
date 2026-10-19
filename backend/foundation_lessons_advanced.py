"""Original tree, graph and optimization lessons for TypeScript practice."""
from .foundation_lessons_core import frame, row
from .foundation_lessons_patterns import guide, scenes


def graph_scene(points, edges, active, note, detail, code=''):
    nodes = [{'id': name, 'label': name, 'x': x, 'y': y, 'active': name in active}
             for name, x, y in points]
    result = frame(nodes, note, detail, code)
    result['edges'] = edges
    return result


TREE = [('A',280,25),('B',150,125),('C',410,125),('D',70,225),('E',230,225)]
TREE_EDGES = [('A','B'),('A','C'),('B','D'),('B','E')]

ADVANCED_LESSONS = [
    dict(
        id='tree-inorder', title='이진 트리 · 중위 순회', group='자료구조', priority=2, difficulty='입문',
        summary='왼쪽 부분 트리, 현재 노드, 오른쪽 부분 트리 순으로 방문합니다.',
        concept='이진 트리의 각 노드는 왼쪽·오른쪽 자식 참조를 가질 수 있습니다. 중위 순회는 왼쪽 전체를 방문한 다음 현재 노드를 기록하고 오른쪽 전체를 방문합니다. 자식이 null이면 돌아옵니다. 같은 방문 규칙을 모든 부분 트리에 재귀적으로 적용합니다.',
        complexity='모든 노드를 한 번 방문해 시간 O(n), 반환 배열 O(n)과 재귀 스택 O(h)를 사용합니다. h는 트리 높이입니다.',
        application='BST에서는 중위 순회의 값이 오름차순으로 나옵니다. 일반 이진 트리에서는 정렬을 보장하지 않습니다.',
        questions=[('루트 A의 왼쪽 B와 오른쪽 C가 있을 때 중위 순서는 무엇인가요?', 'B,A,C 순이다. 각 자식에게도 같은 왼쪽→현재→오른쪽 규칙을 적용한다.'),
                   ('편향된 트리에서 재귀 스택은 얼마나 깊어질 수 있나요?', '높이 h만큼 쌓이며, 모든 노드가 한쪽으로 이어지면 O(n)이다.')],
        requirements=['`inorder(root: TreeNode | null): number[]`를 구현하세요. `TreeNode`는 `value`, `left`, `right`를 가집니다.',
                      '입력을 변경하지 않고 왼쪽→현재→오른쪽 순서로 값을 반환하세요.'],
        starter='''type TreeNode = { value:number; left:TreeNode|null; right:TreeNode|null };
function inorder(root:TreeNode|null):number[] { return []; }''',
        reference='''type TreeNode = { value:number; left:TreeNode|null; right:TreeNode|null };
function inorder(root:TreeNode|null):number[] {
  const result:number[]=[];
  function visit(node:TreeNode|null):void {
    if (node===null) return;
    visit(node.left); result.push(node.value); visit(node.right);
  }
  visit(root); return result;
}''',
        public_tests='''const root={value:4,left:{value:2,left:null,right:null},right:{value:6,left:null,right:null}};
assertEqual(inorder(root),[2,4,6]); assertEqual(inorder(null),[]);''',
        hidden_tests='''const root:TreeNode={value:1,left:{value:2,left:{value:4,left:null,right:null},right:{value:5,left:null,right:null}},right:{value:3,left:null,right:null}};
assertEqual(inorder(root),[4,2,5,1,3]); assertEqual(inorder(root),[4,2,5,1,3]);
assertEqual(inorder({value:0,left:null,right:null}),[0]);''',
        mutations=[('왼쪽 순회', 'visit(node.left);', 'visit(node.right);'),
                   ('노드 값', 'result.push(node.value);', 'result.push(node.value+1);')],
        visualization='tree-inorder', visual_round=True, prerequisites=['linked-list'],
        reading=guide('노드를 기록할 때 왼쪽 부분 트리는 전부 처리되었고 오른쪽 부분 트리는 아직 남았습니다.',
            [['왼쪽으로 내려간다','A에서 B, 다시 D까지 내려갑니다.'],['현재 값을 기록한다','D를 기록하고 돌아와 B, E를 처리합니다.'],['오른쪽으로 옮긴다','왼쪽이 끝난 뒤 A와 오른쪽 C를 기록합니다.']],
            '자식이 null이면 바로 돌아와야 합니다. 중위 순서가 정렬되는 것은 BST 규칙이 있을 때뿐입니다.',
            '반환 배열은 O(n)이고 호출 스택은 트리 높이만큼 필요합니다.',
            'BST의 값을 작은 순서대로 열람할 때 중위 순회를 사용할 수 있습니다.',
            '편향된 트리와 빈 트리에서 호출 순서를 비교하세요.'),
        hints=['왼쪽 자식만 두 단계 깊은 트리에서 순서를 확인하세요.', 'null 자식과 빈 트리에서 멈추는지 확인하세요.'],
        visual_frames=[graph_scene(TREE,TREE_EDGES,(),'루트 A에서 시작합니다.','방문 규칙은 왼쪽→현재→오른쪽입니다.'),
                       graph_scene(TREE,TREE_EDGES,('D',),'왼쪽 끝 D에 도착했습니다.','D에는 왼쪽 자식이 없으므로 D를 먼저 기록합니다.','visit(D.left); record(D)'),
                       graph_scene(TREE,TREE_EDGES,('B','E'),'B를 기록하고 E로 갑니다.','D,B 다음 E를 기록하면 B의 부분 트리가 끝납니다.','D → B → E'),
                       graph_scene(TREE,TREE_EDGES,('A','C'),'A 다음 C를 방문합니다.','전체 결과는 D,B,E,A,C입니다.','return [D,B,E,A,C]')]),
    dict(
        id='bst-search', title='이진 탐색 트리 · 방향 고르기', group='자료구조', priority=2, difficulty='입문',
        summary='현재 값과 목표를 비교해 한쪽 부분 트리만 탐색합니다.',
        concept='BST는 각 노드의 왼쪽에 더 작은 값, 오른쪽에 더 큰 값을 둡니다. 현재 값과 목표를 비교하면 한쪽 부분 트리는 검사할 필요가 없습니다. 이 단원은 중복 값이 없는 트리에서 존재 여부를 구합니다.',
        complexity='트리 높이 h에 비례해 시간 O(h), 반복 구현의 추가 공간 O(1)입니다. 균형이 좋으면 O(log n), 한쪽으로 치우치면 O(n)입니다.',
        application='정렬 상태를 유지한 검색 구조의 기초입니다. 데이터가 계속 들어올 때는 균형을 유지하는 정책이 추가로 필요합니다.',
        questions=[('목표가 현재 값보다 작을 때 오른쪽 부분 트리를 왜 버릴 수 있나요?', 'BST 규칙상 오른쪽 모든 값은 현재 값보다 크므로 목표가 있을 수 없다.'),
                   ('BST의 검색이 항상 O(log n)인가요?', '아니다. 한쪽으로 편향되면 높이가 n이 되어 O(n)이다.')],
        requirements=['중복 없는 BST의 `contains(root: TreeNode | null, target: number): boolean`을 구현하세요.',
                      '노드를 변경하지 마세요.'],
        starter='''type TreeNode={value:number;left:TreeNode|null;right:TreeNode|null};
function contains(root:TreeNode|null,target:number):boolean { return false; }''',
        reference='''type TreeNode={value:number;left:TreeNode|null;right:TreeNode|null};
function contains(root:TreeNode|null,target:number):boolean {
  let node=root;
  while (node!==null) {
    if (target===node.value) return true;
    node=target<node.value?node.left:node.right;
  }
  return false;
}''',
        public_tests='''const root={value:5,left:{value:2,left:null,right:null},right:{value:8,left:null,right:null}};
assertEqual(contains(root,2),true); assertEqual(contains(root,7),false);''',
        hidden_tests='''const root:TreeNode={value:5,left:{value:2,left:{value:-1,left:null,right:null},right:{value:3,left:null,right:null}},right:{value:8,left:null,right:null}};
assertEqual(contains(root,3),true); assertEqual(contains(root,-1),true);
assertEqual(contains(root,5),true); assertEqual(contains(root,6),false);
assertEqual(contains(null,3),false);''',
        mutations=[('탐색 방향', 'target<node.value?node.left:node.right', 'target<node.value?node.right:node.left'),
                   ('같은 값', 'target===node.value', 'target+1===node.value')],
        visualization='bst-search', visual_round=True, prerequisites=['tree-inorder','binary-search'],
        reading=guide('현재 노드의 부분 트리에 목표가 없다면 탐색은 끝나며, 다른 쪽 가지는 이미 버릴 수 있습니다.',
            [['현재 값을 비교한다','목표 5와 루트 8을 비교합니다.'],['한쪽만 선택한다','5는 더 작으므로 왼쪽만 내려갑니다.'],['일치 또는 null에서 종료한다','5를 찾으면 true, 더 내려갈 곳이 없으면 false입니다.']],
            '일반 이진 트리에는 이 규칙을 적용할 수 없습니다. 트리가 편향되면 비교 횟수도 늘어납니다.',
            '균형에 따른 높이가 검색 성능을 결정합니다.',
            '순서를 유지하는 키 검색에 사용할 수 있지만, 균형 유지가 없는 구현은 특정 입력에서 느립니다.',
            '왼쪽만 이어진 트리와 균형 트리의 비교 횟수를 세어보세요.'),
        hints=['루트, 양쪽 손자, 없는 값을 각각 검색하세요.', '목표가 현재 값보다 작은데 반대쪽으로 가지 않는지 확인하세요.'],
        visual_frames=[graph_scene([('8',280,25),('4',150,125),('12',410,125),('2',70,225),('5',230,225)],[('8','4'),('8','12'),('4','2'),('4','5')],('8',),'루트 8과 목표 5를 비교합니다.','5가 작으므로 오른쪽 12의 가지는 버립니다.','5 < 8'),
                       graph_scene([('8',280,25),('4',150,125),('12',410,125),('2',70,225),('5',230,225)],[('8','4'),('8','12'),('4','2'),('4','5')],('4',),'노드 4와 비교합니다.','5는 더 크므로 왼쪽 2의 가지는 버립니다.','5 > 4'),
                       graph_scene([('8',280,25),('4',150,125),('12',410,125),('2',70,225),('5',230,225)],[('8','4'),('8','12'),('4','2'),('4','5')],('5',),'값 5를 찾았습니다.','방문한 노드는 8,4,5 세 개뿐입니다.','return true')]),
    dict(
        id='adjacency-list', title='그래프 · 인접 목록 만들기', group='자료구조', priority=2, difficulty='입문',
        summary='정점과 방향 간선 목록을 각 정점의 이웃 목록으로 바꿉니다.',
        concept='인접 목록은 각 정점에서 직접 갈 수 있는 이웃을 저장합니다. 정점 목록으로 빈 이웃 배열을 먼저 만들고, 각 방향 간선 (from,to)을 from의 목록에 추가합니다. 간선의 입력 순서와 중복도 보존합니다. 간선이 없는 정점도 결과에 있어야 합니다.',
        complexity='정점 V개, 간선 E개를 한 번씩 처리해 시간 O(V+E), 저장 공간 O(V+E)입니다.',
        application='BFS·DFS가 이웃을 빠르게 방문하기 위한 입력 형태로 쓰입니다.',
        questions=[('간선이 없는 정점도 인접 목록에 필요한가요?', '필요하다. 빈 이웃 목록으로 포함해야 그 정점이 그래프에 있다는 사실을 알 수 있다.'),
                   ('방향 간선 A→B가 있으면 B의 목록에도 A를 넣어야 하나요?', '아니다. 방향 그래프에서는 A의 목록에만 B를 넣는다.')],
        requirements=['`adjacencyList(vertices: string[], edges: [string,string][]): Record<string,string[]>`를 구현하세요.',
                      '모든 간선의 양 끝은 정점 목록에 있습니다. 방향·중복·입력 순서를 유지하고 입력을 변경하지 마세요. 특수 키도 안전하게 다루세요.'],
        starter='function adjacencyList(vertices:string[],edges:[string,string][]):Record<string,string[]> { return {}; }',
        reference='''function adjacencyList(vertices:string[],edges:[string,string][]):Record<string,string[]> {
  const graph=Object.create(null) as Record<string,string[]>;
  for (const vertex of vertices) graph[vertex]=[];
  for (const [from,to] of edges) graph[from].push(to);
  return graph;
}''',
        public_tests="assertEqual(adjacencyList(['A','B','C'],[['A','B'],['A','B']]),{A:['B','B'],B:[],C:[]}); assertEqual(adjacencyList([],[]),{});",
        hidden_tests="""const vertices=['__proto__','constructor','Z']; const edges:[string,string][]=[['__proto__','constructor']];
const expected=Object.create(null); expected['__proto__']=['constructor']; expected.constructor=[]; expected.Z=[];
assertEqual(adjacencyList(vertices,edges),expected);
assertEqual(edges,[['__proto__','constructor']]);
assertEqual(adjacencyList(['a'],[['a','a']]),{a:['a']});""",
        mutations=[('고립 정점', 'for (const vertex of vertices) graph[vertex]=[];', 'for (const vertex of vertices.slice(0,-1)) graph[vertex]=[];'),
                   ('방향', 'graph[from].push(to);', 'graph[to].push(from);')],
        visualization='adjacency-list', visual_round=True, prerequisites=['dictionary'],
        reading=guide('각 정점의 배열은 지금까지 읽은 간선 중 그 정점에서 나가는 간선의 도착점을 입력 순서대로 담습니다.',
            [['정점부터 준비한다','A,B,C 모두 빈 배열로 시작합니다.'],['간선을 읽는다','A→B를 읽으면 A의 이웃에 B를 추가합니다.'],['고립 정점을 남긴다','간선이 없는 C는 빈 배열로 보관합니다.']],
            '방향 간선을 자동으로 반대쪽에도 넣으면 다른 그래프가 됩니다. 특수 문자열 키는 일반 객체 속성과 충돌할 수 있습니다.',
            '간선 행렬 O(V²)과 달리 이웃 목록은 O(V+E) 공간이라 희소 그래프에 적합합니다.',
            '업무 의존 관계에서 작업별 다음 작업 목록을 만들 수 있습니다.',
            '중복 간선과 고립 정점 C가 어떻게 기록되는지 보세요.'),
        hints=['고립 정점을 포함한 결과를 검사하세요.', 'A→B만 있을 때 B→A가 생기지 않는지 확인하세요.'],
        visual_frames=[graph_scene([('A',80,110),('B',300,45),('C',500,210)],[],(), '정점 세 개를 준비합니다.','모든 정점의 이웃 목록은 처음에 비어 있습니다.','A: []; B: []; C: []'),
                       graph_scene([('A',80,110),('B',300,45),('C',500,210)],[('A','B')],('A','B'),'A→B 간선을 추가합니다.','A의 목록에 B를 넣고 B의 목록은 그대로 둡니다.','A: [B]'),
                       graph_scene([('A',80,110),('B',300,45),('C',500,210)],[('A','B')],('C',),'고립된 C도 남깁니다.','C는 존재하지만 나가는 간선이 없습니다.','C: []')]),
    dict(
        id='topological-sort', title='위상 정렬 · 선행 순서', group='알고리즘', priority=2, difficulty='보통',
        summary='방향 비순환 그래프에서 모든 선행 작업을 먼저 배치합니다.',
        concept='위상 정렬에서는 모든 간선 u→v에 대해 u가 v보다 앞에 있어야 합니다. 진입 차수가 0인 정점부터 꺼내고, 나가는 간선을 제거한 뒤 새로 0이 된 정점을 대기열에 넣습니다. 가능한 순서가 여러 개일 수 있습니다. 순서에 넣은 정점이 전체보다 적으면 순환이 있어 완전한 순서가 없습니다.',
        complexity='인접 목록과 진입 차수를 만들고 각 정점·간선을 한 번 처리하므로 시간 O(V+E), 공간 O(V+E).',
        application='빌드 작업의 의존 순서나 수강 선수 과목 순서를 계산하는 데 사용합니다.',
        questions=[('진입 차수 0인 정점부터 처리하는 이유는 무엇인가요?', '아직 처리하지 않은 선행 정점이 없어 지금 배치해도 모든 간선 순서를 지킨다.'),
                   ('모든 정점을 꺼내기 전에 대기열이 비면 무엇을 뜻하나요?', '남은 정점 사이에 순환이 있어 유효한 위상 순서를 만들 수 없다.')],
        requirements=['`topologicalOrder(vertices: string[], edges: [string,string][]): string[] | null`을 구현하세요.',
                      '모든 간선 끝점은 정점 목록에 있습니다. 유효한 순서가 여러 개면 아무 것이나 허용합니다. 순환이면 null입니다.'],
        starter='function topologicalOrder(vertices:string[],edges:[string,string][]):string[]|null { return null; }',
        reference='''function topologicalOrder(vertices:string[],edges:[string,string][]):string[]|null {
  const next=new Map<string,string[]>(vertices.map(v=>[v,[]]));
  const indegree=new Map<string,number>(vertices.map(v=>[v,0]));
  for (const [from,to] of edges) { next.get(from)!.push(to); indegree.set(to,indegree.get(to)!+1); }
  const queue=vertices.filter(v=>indegree.get(v)===0), order:string[]=[];
  for (let head=0;head<queue.length;head++) {
    const v=queue[head]; order.push(v);
    for (const neighbor of next.get(v)!) {
      indegree.set(neighbor,indegree.get(neighbor)!-1);
      if (indegree.get(neighbor)===0) queue.push(neighbor);
    }
  }
  return order.length===vertices.length?order:null;
}''',
        public_tests='''const vertices=['A','B','C'], edges:[string,string][]=[['A','C'],['B','C']];
const order=topologicalOrder(vertices,edges);
assertEqual(order!==null,true);
if (order) { assertEqual(order.indexOf('A')<order.indexOf('C'),true); assertEqual(order.indexOf('B')<order.indexOf('C'),true); }''',
        hidden_tests='''function valid(order:string[]|null, vertices:string[], edges:[string,string][]):boolean {
  if (!order || order.length!==vertices.length || new Set(order).size!==vertices.length) return false;
  const position=new Map<string,number>(order.map((v,i)=>[v,i]));
  return vertices.every(v=>position.has(v)) && edges.every(([a,b])=>position.get(a)!<position.get(b)!);
}
const vertices=['A','B','C','D'], edges:[string,string][]=[['A','C'],['B','C'],['C','D']];
assertEqual(valid(topologicalOrder(vertices,edges),vertices,edges),true);
assertEqual(topologicalOrder(['A','B'],[['A','B'],['B','A']]),null);
assertEqual(valid(topologicalOrder(['X','Y'],[]),['X','Y'],[]),true);''',
        mutations=[('진입 차수', 'indegree.get(neighbor)!-1', 'indegree.get(neighbor)!+1'),
                   ('순환 감지', 'order.length===vertices.length?order:null', 'order')],
        visualization='topological-sort', visual_round=True, prerequisites=['adjacency-list','bfs'],
        reading=guide('대기열에 있는 정점은 아직 처리하지 않은 선행 간선이 없습니다.',
            [['진입 차수를 센다','A와 B는 0, C는 2입니다.'],['준비된 작업을 처리한다','A와 B를 먼저 배치하며 C의 남은 선행 수를 줄입니다.'],['순환 여부를 판단한다','모든 정점을 배치했다면 성공, 일부가 남았는데 대기열이 비면 순환입니다.']],
            '여러 올바른 순서가 있으므로 특정 배열 하나와만 비교하면 안 됩니다. 중복 간선도 진입 차수만큼 각각 줄여야 합니다.',
            '정점·간선을 한 번씩 처리하므로 O(V+E)입니다.',
            '작업 빌드에서 선행 작업이 끝나야 다음 작업을 시작하는 순서를 계산합니다.',
            'A와 B의 순서를 바꿔도 C보다 앞이면 모두 유효한지 확인하세요.'),
        hints=['서로 독립된 두 선행 작업의 순서가 달라도 정답으로 인정해보세요.', 'A→B→A 순환을 넣으면 null을 반환하나요?'],
        visual_frames=[graph_scene([('A',80,65),('B',80,235),('C',310,145),('D',520,145)],[('A','C'),('B','C'),('C','D')],('A','B'),'A와 B의 진입 차수는 0입니다.','두 작업의 상대 순서는 어느 쪽이 먼저여도 됩니다.','queue=[A,B]'),
                       graph_scene([('A',80,65),('B',80,235),('C',310,145),('D',520,145)],[('A','C'),('B','C'),('C','D')],('A','B'),'A와 B를 처리합니다.','C의 남은 진입 차수가 2→1→0이 됩니다.','order=[A,B]'),
                       graph_scene([('A',80,65),('B',80,235),('C',310,145),('D',520,145)],[('A','C'),('B','C'),('C','D')],('C','D'),'C 다음 D를 처리합니다.','모든 선행 순서를 만족하는 한 가지 결과 [A,B,C,D]입니다.','return [A,B,C,D]')]),
]

ADVANCED_LESSONS.extend([
    dict(
        id='union-find', title='서로소 집합 · 연결 묶기', group='자료구조', priority=2, difficulty='보통',
        summary='대표 원소를 관리해 두 원소가 같은 묶음인지 확인합니다.',
        concept='서로소 집합은 각 원소가 속한 집합의 대표를 찾습니다. union은 서로 다른 대표를 연결하고, find는 부모 참조를 따라 대표에 도착합니다. 경로 압축은 지나간 노드가 대표를 바로 가리키게 하며 크기가 큰 집합 아래 작은 집합을 붙이면 깊이를 줄일 수 있습니다.',
        complexity='경로 압축과 크기 기준 합치기를 함께 쓰면 연속 m회 연산의 총 비용은 O(m α(n))이고 저장 공간 O(n)입니다.',
        application='네트워크 연결 추가 후 두 장치가 같은 연결 성분에 속하는지 확인하거나 Kruskal 알고리즘에서 순환을 막습니다.',
        questions=[('union(a,b)가 이미 같은 집합인 두 원소를 받으면 어떻게 하나요?', '새 연결은 생기지 않으므로 false를 반환하고 집합 상태를 유지한다.'),
                   ('find의 경로 압축은 무엇을 바꾸나요?', '대표로 가는 경로 위 부모 참조를 대표로 직접 연결해 다음 탐색을 짧게 만든다.')],
        requirements=['`DisjointSet`의 생성자는 양의 정수 `size`를 받습니다. `find(x): number`, `union(a,b): boolean`, `connected(a,b): boolean`을 구현하세요.',
                      '원소는 0 이상 size 미만입니다. union은 서로 다른 집합을 합쳤을 때만 true를 반환합니다.'],
        starter='''class DisjointSet {
  constructor(size:number) {}
  find(x:number):number { return x; }
  union(a:number,b:number):boolean { return false; }
  connected(a:number,b:number):boolean { return false; }
}''',
        reference='''class DisjointSet {
  private parent:number[];
  private sizes:number[];
  constructor(size:number) { this.parent=Array.from({length:size},(_,i)=>i); this.sizes=Array(size).fill(1); }
  find(x:number):number {
    if (this.parent[x]!==x) this.parent[x]=this.find(this.parent[x]);
    return this.parent[x];
  }
  union(a:number,b:number):boolean {
    let x=this.find(a), y=this.find(b);
    if (x===y) return false;
    if (this.sizes[x]<this.sizes[y]) [x,y]=[y,x];
    this.parent[y]=x; this.sizes[x]+=this.sizes[y]; return true;
  }
  connected(a:number,b:number):boolean { return this.find(a)===this.find(b); }
}''',
        public_tests='''const d=new DisjointSet(4);
assertEqual(d.union(0,1),true); assertEqual(d.connected(0,1),true);
assertEqual(d.connected(0,2),false); assertEqual(d.union(1,0),false);''',
        hidden_tests='''const d=new DisjointSet(5);
assertEqual(d.union(0,1),true); assertEqual(d.union(2,3),true);
assertEqual(d.union(1,2),true); assertEqual(d.connected(0,3),true);
assertEqual(d.union(0,3),false); assertEqual(d.connected(4,0),false);
assertEqual(d.find(0),d.find(3)); assertEqual(new DisjointSet(1).connected(0,0),true);''',
        mutations=[('이미 연결됨', 'if (x===y) return false;', 'if (x===y) return true;'),
                   ('대표 연결', 'this.parent[y]=x;', 'this.parent[y]=y;')],
        visualization='union-find', visual_round=True, prerequisites=['adjacency-list'],
        reading=guide('각 원소의 부모 참조를 따라가면 자기 자신을 가리키는 대표에 도착합니다.',
            [['각자 시작한다','0,1,2,3은 처음에는 서로 다른 대표입니다.'],['두 집합을 잇는다','union(0,1)에서 1의 대표가 0을 가리킵니다.'],['대표로 연결을 판단한다','union(1,2) 후 find(0)과 find(2)가 같은지 확인합니다.']],
            '원소 값 자체가 같지 않아도 대표가 같으면 같은 집합입니다. 이미 합쳐진 집합을 다시 잇지 마세요.',
            '경로 압축과 집합 크기 비교는 반복 연산의 비용을 매우 작게 만듭니다.',
            '네트워크 케이블을 추가할 때 두 장치가 이미 연결돼 있다면 새로운 연결은 순환을 만듭니다.',
            '0–1, 2–3을 잇고 다시 1–2를 이어 네 원소가 한 집합이 되는지 보세요.'),
        hints=['두 집합을 각각 만든 뒤 그 집합의 내부 원소끼리 연결해보세요.', '같은 두 원소를 다시 union하면 false인가요?'],
        visual_frames=[graph_scene([('0',65,55),('1',225,55),('2',385,55),('3',545,55)],[],(), '네 원소가 각자 집합입니다.','각 원소의 대표는 자기 자신입니다.','parent=[0,1,2,3]'),
                       graph_scene([('0',65,55),('1',225,55),('2',385,55),('3',545,55)],[('0','1'),('2','3')],('0','1'),'0–1과 2–3을 각각 연결합니다.','아직 두 집합은 분리되어 있습니다.','union(0,1); union(2,3)'),
                       graph_scene([('0',65,55),('1',225,55),('2',385,55),('3',545,55)],[('0','1'),('0','2'),('2','3')],('0','2'),'1과 2를 통해 두 집합을 합칩니다.','이제 0과 3의 대표가 같습니다.','connected(0,3) → true')]),
    dict(
        id='kruskal', title='최소 신장 트리 · 작은 간선부터', group='알고리즘', priority=2, difficulty='보통',
        summary='순환을 만들지 않는 가장 싼 간선을 골라 모든 정점을 잇습니다.',
        concept='최소 신장 트리는 무방향 그래프의 모든 정점을 순환 없이 연결하며 간선 비용 합을 최소화합니다. Kruskal은 간선을 비용 순으로 정렬하고 서로 다른 연결 성분을 잇는 간선만 선택합니다. 서로소 집합으로 두 끝점이 이미 연결됐는지 확인합니다. 연결되지 않은 입력에는 신장 트리가 없습니다.',
        complexity='간선 정렬 O(E log E), 서로소 집합 처리 O(E α(V)), 저장 공간 O(V+E).',
        application='여러 장소를 최소 총 비용의 케이블로 연결하는 계획의 기초가 됩니다.',
        questions=[('간선을 골랐을 때 순환을 만드는지 어떻게 아나요?', '양 끝점이 이미 같은 연결 성분이면 그 간선을 고르면 순환이다.'),
                   ('V개 정점을 잇는 신장 트리에는 간선이 몇 개 필요한가요?', 'V-1개이며, 연결되지 않은 그래프에서는 이 수에 도달할 수 없다.')],
        requirements=['`minimumSpanningWeight(vertexCount: number, edges: [number,number,number][]): number | null`을 구현하세요.',
                      '정점은 0부터 vertexCount-1, 간선은 [u,v,weight]인 무방향 간선입니다. 중복·음수·자기 간선을 허용합니다. 연결 불가능하면 null이고 vertexCount 0 또는 1의 답은 0입니다.'],
        starter='function minimumSpanningWeight(vertexCount:number,edges:[number,number,number][]):number|null { return null; }',
        reference='''function minimumSpanningWeight(vertexCount:number,edges:[number,number,number][]):number|null {
  if (vertexCount<=1) return 0;
  const parent=Array.from({length:vertexCount},(_,i)=>i);
  const find=(x:number):number=>parent[x]===x?x:(parent[x]=find(parent[x]));
  let total=0, chosen=0;
  for (const [u,v,w] of [...edges].sort((a,b)=>a[2]-b[2])) {
    const a=find(u), b=find(v);
    if (a===b) continue;
    parent[b]=a; total+=w; chosen++;
    if (chosen===vertexCount-1) return total;
  }
  return null;
}''',
        public_tests='''assertEqual(minimumSpanningWeight(3,[[0,1,4],[1,2,1],[0,2,2]]),3);
assertEqual(minimumSpanningWeight(2,[]),null);''',
        hidden_tests='''const edges:[number,number,number][]=[[0,1,-2],[1,2,3],[0,2,5],[2,3,1],[3,3,-99]];
assertEqual(minimumSpanningWeight(4,edges),2);
assertEqual(edges,[[0,1,-2],[1,2,3],[0,2,5],[2,3,1],[3,3,-99]]);
assertEqual(minimumSpanningWeight(0,[]),0); assertEqual(minimumSpanningWeight(1,[]),0);
assertEqual(minimumSpanningWeight(3,[[0,1,1]]),null);''',
        mutations=[('비용 순서', 'a[2]-b[2]', 'b[2]-a[2]'),
                   ('연결 불가', 'return null;', 'return total;')],
        visualization='kruskal', visual_round=True, prerequisites=['union-find','priority-queue'],
        reading=guide('선택된 간선은 순환이 없고, 그 시점까지 처리한 간선으로 만들 수 있는 최소 비용 연결을 유지합니다.',
            [['작은 간선부터 본다','비용 1, 2, 4 순으로 간선을 검사합니다.'],['순환을 피한다','끝점의 대표가 같으면 이미 연결돼 있으므로 건너뜁니다.'],['V-1개를 고른다','모든 정점이 연결되면 총 비용을 반환합니다.']],
            '가장 싼 간선이라도 순환을 만들면 선택하지 않습니다. 그래프가 연결되지 않았다면 부분 비용을 정답으로 반환하지 마세요.',
            '정렬이 주된 비용이며 서로소 집합이 연결 판정을 빠르게 합니다.',
            '건물 사이 연결 후보 비용이 주어졌을 때 최소 총 배선 비용을 계산합니다.',
            '비용이 가장 낮은 자기 간선이 왜 선택되지 않는지 확인하세요.'),
        hints=['비용이 가장 작은 간선이 자기 자신으로 이어지는 경우를 시험하세요.', '정점 하나가 고립되면 null이 되는지 확인하세요.'],
        visual_frames=[graph_scene([('0',65,55),('1',270,55),('2',160,225)],[('0','1'),('1','2'),('0','2')],(), '세 간선을 비용순으로 정렬합니다.','0–1 비용 4, 1–2 비용 1, 0–2 비용 2입니다.','1, 2, 4'),
                       graph_scene([('0',65,55),('1',270,55),('2',160,225)],[('0','1'),('1','2'),('0','2')],('1','2'),'비용 1인 1–2를 고릅니다.','서로 다른 집합을 하나로 묶습니다.','total=1'),
                       graph_scene([('0',65,55),('1',270,55),('2',160,225)],[('0','1'),('1','2'),('0','2')],('0','2'),'비용 2인 0–2를 고릅니다.','두 간선으로 세 정점이 모두 연결됐습니다. 비용 4는 필요 없습니다.','return 3')]),
    dict(
        id='dijkstra', title='다익스트라 · 가중 최단 거리', group='알고리즘', priority=2, difficulty='보통',
        summary='음수 간선이 없는 방향 그래프에서 시작점별 최소 비용을 계산합니다.',
        concept='다익스트라는 아직 확정하지 않은 정점 중 시작점으로부터 거리가 가장 작은 정점을 확정합니다. 그 정점의 나가는 간선을 확인해 더 짧은 경로가 있으면 이웃 거리를 갱신합니다. 음수 간선이 없기 때문에 한 번 확정한 최단 거리가 나중에 줄지 않습니다. 이 단원은 작은 그래프를 위한 단순 탐색 버전을 구현합니다.',
        complexity='최솟값 정점을 매번 전체에서 찾는 이 구현은 시간 O(V²+E), 거리·방문·인접 목록 저장 공간 O(V+E)입니다. 힙을 쓰면 다른 비용이 됩니다.',
        application='이동 경로에 서로 다른 양의 비용이 붙는 지도의 최단 이동 비용을 계산할 때 사용합니다.',
        questions=[('가장 짧은 미확정 정점을 확정해도 되는 조건은 무엇인가요?', '모든 간선 가중치가 음수가 아니어서 이후 경로로 이미 확정한 거리가 더 짧아질 수 없다.'),
                   ('BFS를 그대로 쓰면 왜 가중 경로의 최소 비용이 안 나오나요?', 'BFS는 간선 수가 적은 층을 먼저 찾지만 간선마다 비용이 다르면 더 많은 간선의 경로가 더 쌀 수 있다.')],
        requirements=['`shortestPaths(vertexCount: number, edges: [number,number,number][], start: number): (number|null)[]`를 구현하세요.',
                      '정점은 0부터 vertexCount-1, 방향 간선의 비용은 0 이상입니다. 도달할 수 없는 정점은 null로 반환하세요.'],
        starter='function shortestPaths(vertexCount:number,edges:[number,number,number][],start:number):(number|null)[] { return []; }',
        reference='''function shortestPaths(vertexCount:number,edges:[number,number,number][],start:number):(number|null)[] {
  const graph:[number,number][][]=Array.from({length:vertexCount},()=>[]);
  for (const [from,to,cost] of edges) graph[from].push([to,cost]);
  const distance=Array(vertexCount).fill(Infinity) as number[];
  const visited=Array(vertexCount).fill(false) as boolean[];
  distance[start]=0;
  for (let step=0;step<vertexCount;step++) {
    let current=-1;
    for (let v=0;v<vertexCount;v++) if (!visited[v] && (current<0 || distance[v]<distance[current])) current=v;
    if (current<0 || distance[current]===Infinity) break;
    visited[current]=true;
    for (const [next,cost] of graph[current]) distance[next]=Math.min(distance[next],distance[current]+cost);
  }
  return distance.map(value=>value===Infinity?null:value);
}''',
        public_tests='''assertEqual(shortestPaths(3,[[0,1,7],[0,2,2],[2,1,1]],0),[0,3,2]);
assertEqual(shortestPaths(3,[[0,1,1]],0),[0,1,null]);''',
        hidden_tests='''assertEqual(shortestPaths(4,[[0,1,10],[0,2,1],[2,1,2],[1,3,0]],0),[0,3,1,3]);
assertEqual(shortestPaths(2,[[1,0,4]],0),[0,null]);
assertEqual(shortestPaths(1,[],0),[0]);
assertEqual(shortestPaths(3,[[0,1,0],[1,2,0]],0),[0,0,0]);''',
        mutations=[('거리 갱신', 'distance[current]+cost', 'distance[current]+1'),
                   ('최솟값 선택', 'distance[v]<distance[current]', 'distance[v]>distance[current]')],
        visualization='dijkstra', visual_round=True, prerequisites=['bfs','priority-queue'],
        reading=guide('방문 완료한 정점의 거리는 최단 거리로 확정됐습니다.',
            [['시작점을 0으로 둔다','다른 정점의 거리는 아직 모르는 무한대입니다.'],['가장 싼 후보를 확정한다','0→2 비용 2를 먼저 확인해 정점 2의 거리를 확정합니다.'],['이웃을 완화한다','2→1 비용 1을 더해 기존 0→1 비용 7보다 작은 3으로 갱신합니다.']],
            '음수 간선은 이 알고리즘의 확정 근거를 깨뜨립니다. 도달하지 못한 정점은 이 단원의 반환값에서 null입니다.',
            '단순 선택 구현은 O(V²+E)입니다. 큰 희소 그래프에는 힙 기반 구현을 따로 사용합니다.',
            '도로별 이동 시간이 다를 때 시작점에서 각 장소까지 최소 시간을 계산합니다.',
            '간선 수가 더 많아도 총 비용이 더 작은 경로를 비교하세요.'),
        hints=['직접 간선보다 중간 정점을 거치는 경로가 더 싼 입력을 사용하세요.', '도달 불가능한 정점과 비용 0인 간선을 확인하세요.'],
        visual_frames=[graph_scene([('0',70,130),('1',320,35),('2',320,225)],[('0','1'),('0','2'),('2','1')],('0',),'시작점 0의 거리를 확정합니다.','직접 비용은 0→1이 7, 0→2가 2입니다.','distance=[0,7,2]'),
                       graph_scene([('0',70,130),('1',320,35),('2',320,225)],[('0','1'),('0','2'),('2','1')],('2',),'미확정 중 거리 2가 가장 작습니다.','정점 2를 먼저 확정합니다.','current=2'),
                       graph_scene([('0',70,130),('1',320,35),('2',320,225)],[('0','1'),('0','2'),('2','1')],('1',),'2를 거쳐 1의 거리를 갱신합니다.','2+1=3이 직접 비용 7보다 작습니다.','distance[1]=3')]),
    dict(
        id='interval-scheduling', title='그리디 · 겹치지 않는 일정', group='알고리즘', priority=2, difficulty='입문',
        summary='가장 빨리 끝나는 일정부터 골라 선택 개수를 최대화합니다.',
        concept='반열림 구간 [start,end)의 일정들에서 겹치지 않는 최대 개수를 고르려면 종료 시각이 빠른 순서로 정렬합니다. 처음 가능한 일정을 고르면 뒤에 남는 시간이 가장 많습니다. 다음 일정의 시작이 이전 종료 이상이면 함께 선택할 수 있습니다.',
        complexity='정렬 O(n log n), 한 번 순회 O(n), 정렬 복사 공간 O(n).',
        application='한 회의실에 배치할 수 있는 최대 회의 수를 계산합니다.',
        questions=[('왜 가장 일찍 시작하는 일정부터 고르면 안 되나요?', '일찍 시작해도 매우 늦게 끝나면 뒤의 여러 일정을 막을 수 있다. 빨리 끝나는 일정을 고르면 남는 선택지가 많다.'),
                   ('이전 일정이 3에 끝나고 다음이 3에 시작하면 겹치나요?', '반열림 구간이므로 겹치지 않는다. 시작이 이전 종료 이상이면 선택할 수 있다.')],
        requirements=['`maxMeetings(intervals: [number,number][]): number`를 구현하세요.',
                      '각 일정은 start<end인 반열림 구간입니다. 입력을 변경하지 마세요.'],
        starter='function maxMeetings(intervals:[number,number][]):number { return 0; }',
        reference='''function maxMeetings(intervals:[number,number][]):number {
  const sorted=[...intervals].sort((a,b)=>a[1]-b[1]);
  let lastEnd=-Infinity, count=0;
  for (const [start,end] of sorted) if (start>=lastEnd) { count++; lastEnd=end; }
  return count;
}''',
        public_tests='assertEqual(maxMeetings([[1,4],[2,3],[3,5]]),2); assertEqual(maxMeetings([]),0);',
        hidden_tests='''const a:[number,number][]=[[1,10],[2,3],[3,4],[4,5]];
assertEqual(maxMeetings(a),3); assertEqual(a,[[1,10],[2,3],[3,4],[4,5]]);
assertEqual(maxMeetings([[-4,-2],[-2,0],[0,1]]),3);
assertEqual(maxMeetings([[1,2],[1,2]]),1);''',
        mutations=[('정렬 기준', 'a[1]-b[1]', 'a[0]-b[0]'),
                   ('맞닿는 경계', 'start>=lastEnd', 'start>lastEnd')],
        visualization='interval-scheduling', prerequisites=['quick-sort'],
        reading=guide('선택한 일정은 겹치지 않으며, 같은 선택 개수라면 지금까지의 종료 시각을 가장 빠르게 유지합니다.',
            [['종료 시각순 정렬','빨리 끝나는 [2,3)을 먼저 봅니다.'],['가능하면 선택','다음 시작이 현재 종료 이상이면 선택합니다.'],['긴 일정은 건너뛴다','[1,10)을 고르면 뒤의 일정을 막으므로 이 경우에는 선택하지 않습니다.']],
            '정렬을 시작 시각으로 하면 긴 일정 하나 때문에 더 많은 짧은 일정을 놓칠 수 있습니다.',
            '정렬이 주된 비용이며 이후에는 각 일정을 한 번만 확인합니다.',
            '공유 회의실에 최대한 많은 회의를 배치하는 기본 모델입니다.',
            '시작이 같은 두 일정 중 어느 쪽이 더 많은 선택을 남기는지 살펴보세요.'),
        hints=['길고 일찍 시작하는 일정 하나와 짧은 일정 여러 개를 비교하세요.', '앞 일정 종료와 다음 일정 시작이 같은 입력을 검사하세요.'],
        visual_frames=scenes(
            (['1–4','2–3','3–5'],(1,),'가장 빨리 끝나는 [2,3)을 고릅니다.','종료 시각이 작을수록 남는 시간이 많습니다.','lastEnd=3'),
            (['1–4','2–3','3–5'],(2,),'[3,5)가 바로 이어집니다.','반열림 구간이므로 3에서 맞닿아도 겹치지 않습니다.','3 >= 3'),
            (['1–4','2–3','3–5'],(1,2),'두 일정을 선택했습니다.','[1,4)는 두 일정과 겹쳐 함께 고를 수 없습니다.','return 2'))),
])

ADVANCED_LESSONS.extend([
    dict(
        id='deque', title='덱 · 양쪽에서 넣고 꺼내기', group='자료구조', priority=2, difficulty='보통',
        summary='앞·뒤 인덱스를 이동하며 양끝 연산을 처리합니다.',
        concept='덱은 앞과 뒤 양쪽에서 값을 넣고 꺼낼 수 있습니다. head와 tail을 빈 구간의 양끝 경계로 두고 Map<index,value>에 값이 있는 칸만 저장하면 앞에 넣을 때 head를 줄이고, 뒤에 넣을 때 tail을 늘릴 수 있습니다. 비었을 때는 두 경계를 다시 0으로 맞춥니다.',
        complexity='Map 조회·삽입·삭제의 평균 비용을 O(1)로 보면 네 가지 양끝 연산 모두 평균 O(1), 저장 공간 O(n)입니다.',
        application='작업을 앞·뒤 우선순위에 따라 넣거나, 슬라이딩 윈도의 후보를 양쪽에서 제거하는 기본 구조입니다.',
        questions=[('뒤에 넣은 값과 앞에 넣은 값을 각각 어디서 꺼낼 수 있나요?', '덱에서는 앞·뒤 모두 꺼낼 수 있다. 앞에 넣은 값은 popFront로 먼저, 뒤에 넣은 값은 popBack으로 먼저 꺼낼 수 있다.'),
                   ('비었을 때 양끝 경계는 어떤 관계인가요?', 'head와 tail이 같고 저장된 값이 없다.')],
        requirements=['숫자 전용 `Deque`의 `pushFront`, `pushBack`, `popFront`, `popBack`, `size`를 구현하세요.',
                      'push 메서드는 void, pop 메서드는 `number | undefined`를 반환합니다. 각 인스턴스는 독립적입니다.'],
        starter='''class Deque {
  pushFront(value:number):void {}
  pushBack(value:number):void {}
  popFront():number|undefined { return undefined; }
  popBack():number|undefined { return undefined; }
  size():number { return 0; }
}''',
        reference='''class Deque {
  private values=new Map<number,number>();
  private head=0; private tail=0;
  pushFront(value:number):void { this.values.set(--this.head,value); }
  pushBack(value:number):void { this.values.set(this.tail++,value); }
  popFront():number|undefined {
    if (this.head===this.tail) return undefined;
    const value=this.values.get(this.head); this.values.delete(this.head++);
    if (this.head===this.tail) this.head=this.tail=0;
    return value;
  }
  popBack():number|undefined {
    if (this.head===this.tail) return undefined;
    const index=--this.tail, value=this.values.get(index); this.values.delete(index);
    if (this.head===this.tail) this.head=this.tail=0;
    return value;
  }
  size():number { return this.tail-this.head; }
}''',
        public_tests='''const d=new Deque(); d.pushBack(1); d.pushFront(2); d.pushBack(3);
assertEqual(d.size(),3); assertEqual([d.popFront(),d.popBack(),d.popFront()],[2,3,1]);''',
        hidden_tests='''const d=new Deque(); assertEqual(d.popFront(),undefined); assertEqual(d.popBack(),undefined);
d.pushFront(0); d.pushFront(-1); assertEqual(d.popBack(),0); assertEqual(d.popFront(),-1);
d.pushBack(7); assertEqual(d.popFront(),7); assertEqual(d.size(),0);
d.pushBack(8); d.pushFront(9); assertEqual(d.popBack(),8); assertEqual(d.popBack(),9);
assertEqual(new Deque().size(),0);''',
        mutations=[('앞에서 꺼내기', 'const value=this.values.get(this.head);', 'const value=this.values.get(this.tail-1);'),
                   ('뒤에서 꺼내기', 'const index=--this.tail', 'const index=this.head')],
        visualization='deque', prerequisites=['queue'],
        reading=guide('Map에는 [head,tail) 범위의 인덱스마다 정확히 하나의 값이 있습니다.',
            [['앞에 추가한다','head를 줄인 뒤 그 위치에 값을 씁니다.'],['뒤에 추가한다','tail 위치에 쓴 뒤 tail을 늘립니다.'],['각 끝에서 제거한다','해당 인덱스를 읽고 Map에서 지우며 경계를 안쪽으로 옮깁니다.']],
            '빈 덱에서 제거할 때 인덱스를 먼저 움직이지 마세요. 이미 제거한 값을 Map에 남기면 공간이 불필요하게 늘어납니다.',
            '배열 앞에서 shift·unshift를 반복하는 방식은 원소를 이동할 수 있습니다. 인덱스 기반은 평균 O(1)입니다.',
            '새 작업을 앞에 긴급 배치하거나 뒤에 일반 배치하는 대기열을 만들 수 있습니다.',
            '양끝에서 번갈아 넣고 빼며 남은 값의 순서를 확인하세요.'),
        hints=['앞과 뒤에 번갈아 넣어 중간 상태를 확인하세요.', '모두 비운 뒤 다시 넣었을 때도 양쪽 제거가 정확한지 보세요.'],
        visual_frames=scenes(
            ([2,1,3],(0,),'앞에 2, 뒤에 1과 3이 있습니다.','논리적 순서는 [2,1,3]입니다.','head → 2, tail → 3'),
            ([1,3],(0,),'앞에서 2를 꺼냅니다.','남은 순서는 [1,3]입니다.','popFront() → 2'),
            ([1],(0,),'뒤에서 3을 꺼냅니다.','남은 순서는 [1]입니다.','popBack() → 3'))),
    dict(
        id='trie', title='트라이 · 접두사 따라가기', group='자료구조', priority=2, difficulty='보통',
        summary='문자를 간선으로 연결해 단어와 접두사의 존재를 구분합니다.',
        concept='트라이는 루트에서 문자마다 다음 노드로 이동합니다. 같은 접두사로 시작하는 단어는 경로의 앞부분을 공유합니다. 단어가 끝나는 노드에는 별도의 끝 표시가 필요하므로 접두사가 존재하는 것과 단어 자체가 저장됐다는 사실을 구분할 수 있습니다.',
        complexity='길이 L인 단어의 삽입·검색·접두사 검색은 O(L). 노드 저장 공간은 최악 전체 입력 문자 수에 비례합니다.',
        application='검색어 자동완성에서 입력한 접두사로 시작하는 단어 후보를 찾는 구조의 기초입니다.',
        questions=[('car만 저장한 뒤 ca의 접두사 존재와 완전한 단어 존재는 각각 무엇인가요?', 'startsWith(ca)는 true, has(ca)는 false다. ca 노드는 있지만 단어 끝 표시가 없다.'),
                   ('car와 cat를 저장할 때 어떤 부분을 공유하나요?', '루트에서 c, a까지의 경로를 공유하고 r과 t에서 갈라진다.')],
        requirements=['소문자 영문 단어용 `Trie`의 `insert(word): void`, `has(word): boolean`, `startsWith(prefix): boolean`을 구현하세요.',
                      '빈 문자열을 단어로 삽입할 수 있습니다. 빈 접두사는 항상 존재하며 각 인스턴스는 독립적입니다.'],
        starter='''class Trie {
  insert(word:string):void {}
  has(word:string):boolean { return false; }
  startsWith(prefix:string):boolean { return false; }
}''',
        reference='''type TrieNode={children:Map<string,TrieNode>;end:boolean};
class Trie {
  private root:TrieNode={children:new Map(),end:false};
  insert(word:string):void {
    let node=this.root;
    for (const ch of word) {
      if (!node.children.has(ch)) node.children.set(ch,{children:new Map(),end:false});
      node=node.children.get(ch)!;
    }
    node.end=true;
  }
  private walk(word:string):TrieNode|undefined {
    let node:TrieNode|undefined=this.root;
    for (const ch of word) node=node?.children.get(ch);
    return node;
  }
  has(word:string):boolean { return this.walk(word)?.end ?? false; }
  startsWith(prefix:string):boolean { return this.walk(prefix)!==undefined; }
}''',
        public_tests="const t=new Trie(); t.insert('car'); assertEqual(t.has('car'),true); assertEqual(t.has('ca'),false); assertEqual(t.startsWith('ca'),true);",
        hidden_tests="""const t=new Trie(); assertEqual(t.startsWith(''),true); assertEqual(t.has(''),false);
t.insert('cat'); t.insert('car'); t.insert('');
assertEqual(t.has(''),true); assertEqual(t.has('cat'),true); assertEqual(t.has('car'),true);
assertEqual(t.startsWith('cab'),false); assertEqual(t.has('cart'),false);
assertEqual(new Trie().has('car'),false);""",
        mutations=[('단어 끝', 'node.end=true;', 'node.end=false;'),
                   ('접두사 구분', 'this.walk(prefix)!==undefined', 'this.walk(prefix)?.end===true')],
        visualization='trie', visual_round=True, prerequisites=['tree-inorder','dictionary'],
        reading=guide('공유 접두사의 노드는 재사용되고, end만 완전한 단어 여부를 표시합니다.',
            [['문자를 따라간다','car를 넣을 때 c→a→r 경로를 만듭니다.'],['갈라지는 문자만 추가','cat는 c→a를 공유하고 t 가지만 추가합니다.'],['끝 표시로 구분','ca 경로는 있지만 단어 끝은 아니므로 has(ca)는 false입니다.']],
            '경로가 있다는 사실만으로 단어가 저장됐다고 판단하면 접두사 ca를 잘못된 단어로 반환합니다.',
            '길이 L의 검색은 전체 단어 수 대신 L에 비례합니다. 노드 객체와 Map의 저장 비용은 추가됩니다.',
            '검색어 접두사에 맞는 후보를 탐색하는 출발점입니다.',
            'car와 cat를 넣고 ca, car, cart의 결과를 비교하세요.'),
        hints=['단어의 중간 접두사를 has와 startsWith에 각각 넣어보세요.', '빈 문자열과 같은 접두사에서 갈라지는 단어 두 개를 확인하세요.'],
        visual_frames=[graph_scene([('root',35,135),('c',160,135),('a',285,135),('r',425,55),('t',425,225)],[('root','c'),('c','a'),('a','r')],('r',),'car를 저장합니다.','r 노드에 단어 끝 표시를 합니다.','end(r)=true'),
                       graph_scene([('root',35,135),('c',160,135),('a',285,135),('r',425,55),('t',425,225)],[('root','c'),('c','a'),('a','r'),('a','t')],('t',),'cat는 앞 두 문자를 공유합니다.','a에서 새 t 가지만 추가하고 끝 표시를 합니다.','end(t)=true'),
                       graph_scene([('root',35,135),('c',160,135),('a',285,135),('r',425,55),('t',425,225)],[('root','c'),('c','a'),('a','r'),('a','t')],('a',),'ca는 접두사입니다.','a에 끝 표시는 없으므로 has(ca)는 false입니다.','startsWith(ca)=true')]),
    dict(
        id='coin-change', title='동적 계획법 · 최소 동전 수', group='알고리즘', priority=2, difficulty='보통',
        summary='더 작은 금액의 답을 이용해 목표 금액의 최소 동전 수를 구합니다.',
        concept='dp[x]를 금액 x를 만드는 최소 동전 수로 정의합니다. dp[0]=0으로 두고 각 금액 x에서 사용 가능한 동전 c에 대해 dp[x-c]+1 중 가장 작은 값을 택합니다. 만들 수 없는 상태는 무한대로 구분하고 마지막에도 불가능하면 -1을 반환합니다. 동전은 무제한 사용할 수 있습니다.',
        complexity='금액 A와 동전 종류 C에 대해 시간 O(A·C), 표 공간 O(A).',
        application='거스름돈을 최소 동전 개수로 만드는 경우에 쓰지만, 실제 화폐 시스템의 거스름돈 규칙은 별도 제약이 있을 수 있습니다.',
        questions=[('금액 x에 동전 c를 마지막으로 썼다면 이전 상태는 무엇인가요?', '금액 x-c를 만드는 최소 동전 수 dp[x-c]이며 여기에 1을 더한다.'),
                   ('만들 수 없는 금액을 0으로 표시하면 어떤 문제가 생기나요?', '가능한 최소값 0과 구별할 수 없다. 무한대처럼 별도 상태가 필요하다.')],
        requirements=['`minCoins(coins: number[], amount: number): number`를 구현하세요.',
                      '동전 값은 중복 없는 양의 정수이고 무제한 사용 가능합니다. amount는 0 이상입니다. 불가능하면 -1입니다.'],
        starter='function minCoins(coins:number[],amount:number):number { return -1; }',
        reference='''function minCoins(coins:number[],amount:number):number {
  const dp=Array(amount+1).fill(Infinity) as number[];
  dp[0]=0;
  for (let value=1;value<=amount;value++)
    for (const coin of coins)
      if (coin<=value) dp[value]=Math.min(dp[value],dp[value-coin]+1);
  return dp[amount]===Infinity?-1:dp[amount];
}''',
        public_tests='assertEqual(minCoins([1,3,4],6),2); assertEqual(minCoins([2],3),-1);',
        hidden_tests='''assertEqual(minCoins([],0),0); assertEqual(minCoins([],5),-1);
assertEqual(minCoins([2,5],10),2); assertEqual(minCoins([1,3,4],0),0);
assertEqual(minCoins([2,4],7),-1); assertEqual(minCoins([1,5,7],11),3);''',
        mutations=[('최소값', 'Math.min(dp[value],dp[value-coin]+1)', 'Math.max(dp[value],dp[value-coin]+1)'),
                   ('불가능한 금액', 'dp[amount]===Infinity?-1:dp[amount]', 'dp[amount]')],
        visualization='coin-change', prerequisites=['dp-climb'],
        reading=guide('dp[x]는 x보다 작은 상태를 사용해 계산한 최소 동전 수이거나 아직 불가능한 상태입니다.',
            [['0을 초기화한다','금액 0은 동전 0개로 만듭니다.'],['작은 금액부터 채운다','동전 1,3,4로 3은 1개, 4도 1개로 만들 수 있습니다.'],['마지막 동전을 비교','6은 3+3으로 2개가 가장 적습니다.']],
            '특정 화폐에서는 가장 큰 동전을 먼저 고르는 그리디가 실패할 수 있습니다. [1,3,4]로 6을 만들면 4+1+1보다 3+3이 낫습니다.',
            '금액에 비례하는 표를 만들기 때문에 목표 금액이 매우 크면 비용이 큽니다.',
            '종류가 제한된 쿠폰·토큰을 조합해 목표 값에 도달하는 최소 횟수를 구할 수 있습니다.',
            '[1,3,4]에서 금액 0부터 6까지 표를 직접 채워보세요.'),
        hints=['[1,3,4]로 6을 만들 때 큰 동전부터 고르는 방식과 비교하세요.', '도달 불가능한 금액과 금액 0을 구별해보세요.'],
        visual_frames=scenes(
            ([0,-1,-1,-1,-1,-1,-1],(0,),'dp[0]=0으로 시작합니다.','-1 표시는 아직 만들 수 없음을 나타냅니다.','dp[0]=0'),
            ([0,1,2,1,1,2,-1],(3,4),'작은 금액을 차례로 채웁니다.','3과 4는 동전 하나로 만들 수 있습니다.','dp[3]=1; dp[4]=1'),
            ([0,1,2,1,1,2,2],(6,),'금액 6은 3+3이 최소입니다.','동전 4+1+1의 3개보다 2개가 적습니다.','return 2'))),
    dict(
        id='next-greater', title='단조 스택 · 다음 큰 값', group='알고리즘', priority=2, difficulty='보통',
        summary='아직 더 큰 값을 만나지 못한 인덱스를 스택에 남깁니다.',
        concept='오른쪽에서 처음 만나는 엄격히 큰 값을 찾습니다. 아직 답이 없는 인덱스를 스택에 값이 감소하는 순서로 보관합니다. 새 값이 스택 위 값보다 크면 그 위 인덱스의 답을 새 값으로 확정하고 꺼냅니다. 끝까지 남은 인덱스의 답은 -1입니다.',
        complexity='각 인덱스가 한 번 들어가고 한 번 나오므로 전체 시간 O(n), 스택·결과 공간 O(n).',
        application='날짜별 수치가 나중에 처음 증가하는 지점을 찾는 문제의 기본 형태입니다.',
        questions=[('새 값이 스택 위보다 크면 무엇을 확정할 수 있나요?', '스택 위 인덱스의 오른쪽에서 처음 만나는 큰 값이 현재 값이다.'),
                   ('같은 값도 더 큰 값으로 처리하나요?', '아니다. 엄격히 큰 값을 찾으므로 같은 값은 스택에 남긴다.')],
        requirements=['`nextGreater(values: number[]): number[]`를 구현하세요.', '각 위치에서 오른쪽의 첫 엄격히 큰 값 또는 -1을 반환하세요. 입력은 변경하지 마세요.'],
        starter='function nextGreater(values:number[]):number[] { return []; }',
        reference='''function nextGreater(values:number[]):number[] {
  const result=Array(values.length).fill(-1) as number[], stack:number[]=[];
  for (let i=0;i<values.length;i++) {
    while (stack.length && values[stack[stack.length-1]]<values[i]) result[stack.pop()!]=values[i];
    stack.push(i);
  }
  return result;
}''',
        public_tests='assertEqual(nextGreater([2,1,3]),[3,3,-1]); assertEqual(nextGreater([]),[]);',
        hidden_tests='''const a=[2,2,1,3]; assertEqual(nextGreater(a),[3,3,3,-1]);
assertEqual(nextGreater([5,4,3]),[-1,-1,-1]); assertEqual(nextGreater([-2,-1]),[-1,-1]);
assertEqual(nextGreater([1]),[-1]); assertEqual(a,[2,2,1,3]);''',
        mutations=[('엄격히 큰 값', 'values[stack[stack.length-1]]<values[i]', 'values[stack[stack.length-1]]<=values[i]'),
                   ('답의 값', 'result[stack.pop()!]=values[i]', 'result[stack.pop()!]=i')],
        visualization='next-greater', prerequisites=['stack'],
        reading=guide('스택에는 아직 오른쪽의 큰 값을 찾지 못한 인덱스가 있고, 그 값은 아래에서 위로 감소합니다.',
            [['인덱스를 쌓는다','2 다음 1은 더 크지 않으므로 둘 다 남깁니다.'],['큰 값에서 꺼낸다','3을 만나면 1과 2의 답을 모두 3으로 확정합니다.'],['남은 값은 -1','3의 오른쪽에는 큰 값이 없습니다.']],
            '같은 값은 엄격히 크지 않습니다. 스택에는 값이 아니라 인덱스를 넣어 결과 위치를 알 수 있게 합니다.',
            '중첩 비교로 O(n²) 찾을 수 있지만, 각 원소를 한 번만 넣고 꺼내 O(n)에 해결합니다.',
            '향후 처음으로 더 큰 측정값이 나오는 값을 조회할 때 응용할 수 있습니다.',
            '[2,2,1,3]에서 중복 2가 어떻게 남아 있는지 확인하세요.'),
        hints=['같은 값이 여러 번 나와도 그 자체를 답으로 쓰지 않는지 확인하세요.', '큰 값 하나가 앞선 여러 인덱스의 답이 되는 경우를 시험하세요.'],
        visual_frames=scenes(
            ([2,1,3],(0,),'2는 아직 큰 값을 만나지 못했습니다.','인덱스 0을 스택에 넣습니다.','stack=[0]'),
            ([2,1,3],(1,),'1도 스택에 넣습니다.','1은 2보다 작아 앞선 답을 확정하지 못합니다.','stack=[0,1]'),
            ([2,1,3],(2,),'3이 1과 2의 답을 확정합니다.','스택에서 두 인덱스를 꺼내 각각의 답에 3을 씁니다.','result=[3,3,-1]'))),
])

ADVANCED_LESSONS.extend([
    dict(
        id='tree-height', title='이진 트리 · 높이 계산', group='알고리즘', priority=2, difficulty='입문',
        summary='왼쪽·오른쪽 부분 트리의 높이를 합쳐 전체 높이를 구합니다.',
        concept='트리 높이를 노드 수로 정의하면 빈 트리의 높이는 0이고, 현재 노드의 높이는 1+max(왼쪽 높이, 오른쪽 높이)입니다. 자식의 값을 구한 뒤 부모의 값을 계산하므로 후위 방식의 재귀가 적합합니다.',
        complexity='각 노드를 한 번 방문해 시간 O(n), 재귀 스택 O(h)입니다. h는 트리 높이입니다.',
        application='트리의 깊이에 따라 화면 단계나 탐색 비용을 예상할 때 사용합니다.',
        questions=[('빈 트리와 자식 없는 노드의 높이는 각각 얼마인가요?', '빈 트리는 0, 자식 없는 노드는 1이다.'),
                   ('부모의 높이를 계산하려면 무엇을 먼저 알아야 하나요?', '왼쪽과 오른쪽 부분 트리의 높이를 먼저 알아야 한다.')],
        requirements=['`treeHeight(root: TreeNode | null): number`를 구현하세요. 높이는 노드 수 기준입니다.', '노드를 변경하지 마세요.'],
        starter='''type TreeNode={value:number;left:TreeNode|null;right:TreeNode|null};
function treeHeight(root:TreeNode|null):number { return 0; }''',
        reference='''type TreeNode={value:number;left:TreeNode|null;right:TreeNode|null};
function treeHeight(root:TreeNode|null):number {
  if (root===null) return 0;
  return 1+Math.max(treeHeight(root.left),treeHeight(root.right));
}''',
        public_tests='''assertEqual(treeHeight(null),0);
assertEqual(treeHeight({value:1,left:null,right:null}),1);''',
        hidden_tests='''const root:TreeNode={value:1,left:{value:2,left:{value:3,left:null,right:null},right:null},right:{value:4,left:null,right:null}};
assertEqual(treeHeight(root),3); assertEqual(treeHeight(root.right),1);
assertEqual(treeHeight({value:9,left:null,right:{value:8,left:null,right:null}}),2);''',
        mutations=[('긴 가지', 'Math.max(treeHeight(root.left),treeHeight(root.right))', 'Math.min(treeHeight(root.left),treeHeight(root.right))'),
                   ('현재 노드', 'return 1+Math.max', 'return Math.max')],
        visualization='tree-height', visual_round=True, prerequisites=['tree-inorder'],
        reading=guide('높이를 계산한 부분 트리의 결과는 그 아래 가장 긴 노드 경로 길이입니다.',
            [['빈 트리에서 멈춘다','null이면 높이 0을 반환합니다.'],['양쪽 높이를 구한다','B 아래의 긴 경로는 B→D로 두 노드입니다.'],['큰 쪽에 현재를 더한다','A의 높이는 1+max(2,1)=3입니다.']],
            '두 자식의 높이 합은 높이가 아닙니다. 큰 쪽만 현재 노드와 연결됩니다.',
            '모든 노드를 읽지만 추가 스택 크기는 높이에 달려 있습니다.',
            '트리 형태의 메뉴에서 최대 중첩 단계를 계산할 수 있습니다.',
            '한쪽으로만 길게 이어진 트리와 균형 트리를 비교하세요.'),
        hints=['왼쪽과 오른쪽 높이가 다른 트리를 만드세요.', '빈 트리와 단일 노드의 높이를 확인하세요.'],
        visual_frames=[graph_scene(TREE,TREE_EDGES,('D','E','C'),'잎 D, E, C의 높이는 1입니다.','자식이 모두 null입니다.','height(leaf)=1'),
                       graph_scene(TREE,TREE_EDGES,('B',),'B의 높이를 구합니다.','두 자식 높이가 1이므로 B의 높이는 2입니다.','1+max(1,1)=2'),
                       graph_scene(TREE,TREE_EDGES,('A',),'A의 높이는 3입니다.','왼쪽 높이 2가 오른쪽 높이 1보다 큽니다.','1+max(2,1)=3')]),
    dict(
        id='bfs-distances', title='BFS · 최소 간선 수', group='알고리즘', priority=2, difficulty='입문',
        summary='시작 정점에서 각 정점까지 필요한 최소 간선 수를 계산합니다.',
        concept='비가중 방향 그래프에서 BFS는 시작점으로부터 간선 수가 적은 층부터 확장합니다. 시작점 거리를 0으로 두고 새로운 이웃을 처음 발견할 때 부모 거리+1을 기록합니다. 발견하면서 바로 기록하면 순환과 공유 이웃의 중복 예약을 막습니다.',
        complexity='인접 목록 기준 시간 O(V+E), 거리 기록과 큐 공간 O(V).',
        application='친구 관계에서 1단계·2단계 떨어진 사람을 찾거나, 동일 비용의 이동만 있는 길찾기에 사용합니다.',
        questions=[('이웃을 처음 발견할 때 거리를 얼마로 기록하나요?', '현재 정점의 거리+1이며, 큐에 넣을 때 바로 기록한다.'),
                   ('간선 비용이 서로 다르면 이 결과가 최소 비용인가요?', '아니다. BFS는 최소 간선 수이고, 다른 비용에는 가중 최단 경로 알고리즘이 필요하다.')],
        requirements=['`bfsDistances(graph: Record<string,string[]>, start: string): Record<string,number>`를 구현하세요.',
                      '방향 그래프입니다. 시작점은 결과에 거리 0으로 넣고 도달할 수 없는 정점은 결과에서 제외하세요. 없는 키의 이웃은 빈 목록으로 취급하세요.'],
        starter='function bfsDistances(graph:Record<string,string[]>,start:string):Record<string,number> { return {}; }',
        reference='''function bfsDistances(graph:Record<string,string[]>,start:string):Record<string,number> {
  const distance=Object.create(null) as Record<string,number>;
  distance[start]=0; const queue=[start];
  for (let head=0;head<queue.length;head++) {
    const node=queue[head];
    for (const next of Object.hasOwn(graph,node)?graph[node]:[]) {
      if (!Object.hasOwn(distance,next)) { distance[next]=distance[node]+1; queue.push(next); }
    }
  }
  return distance;
}''',
        public_tests="""const result=bfsDistances({A:['B','C'],B:['D'],C:['D'],D:[]},'A');
assertEqual(result.A,0); assertEqual(result.B,1); assertEqual(result.C,1); assertEqual(result.D,2);""",
        hidden_tests="""const result=bfsDistances({A:['A','B','B'],B:['A'],Z:[]},'A');
assertEqual(result.A,0); assertEqual(result.B,1); assertEqual(Object.hasOwn(result,'Z'),false);
assertEqual(bfsDistances({},'toString').toString,0);
const specialGraph=Object.create(null); specialGraph['__proto__']=['constructor']; specialGraph.constructor=[];
const special=bfsDistances(specialGraph,'__proto__');
assertEqual(special['__proto__'],0); assertEqual(special.constructor,1);""",
        mutations=[('이웃 거리', 'distance[node]+1', 'distance[node]'),
                   ('중복 발견', '!Object.hasOwn(distance,next)', 'Object.hasOwn(distance,next)')],
        visualization='bfs-distances', visual_round=True, prerequisites=['bfs','adjacency-list'],
        reading=guide('큐의 정점은 이미 최소 간선 수로 발견됐으며, 아직 처리하지 않은 정점의 거리는 처리 중인 층 이상입니다.',
            [['시작을 0으로 기록','A를 큐에 넣고 거리 0을 둡니다.'],['한 층씩 확장','A의 이웃 B,C를 거리 1로 기록합니다.'],['공유 이웃은 한 번만','B,C 모두 D로 이어져도 D는 처음 발견할 때 거리 2로 기록합니다.']],
            '발견 표시를 늦추면 공유 이웃이 큐에 여러 번 들어갑니다. 도달 불가능한 정점은 값 0이 아니라 결과에서 빠집니다.',
            '간선 가중치가 없거나 모두 동일할 때 최소 이동 횟수를 구합니다.',
            '친구 관계에서 몇 단계 떨어진 사람인지 계산합니다.',
            'A→B, A→C, B→D, C→D와 고립된 Z를 사용해보세요.'),
        hints=['두 경로가 같은 정점으로 합쳐지는 그래프를 검사하세요.', '고립 정점과 특수 이름의 정점도 확인하세요.'],
        visual_frames=[graph_scene([('A',55,130),('B',245,55),('C',245,220),('D',485,130)],[('A','B'),('A','C'),('B','D'),('C','D')],('A',),'A의 거리를 0으로 기록합니다.','큐에 A를 넣고 시작합니다.','distance[A]=0'),
                       graph_scene([('A',55,130),('B',245,55),('C',245,220),('D',485,130)],[('A','B'),('A','C'),('B','D'),('C','D')],('B','C'),'B와 C를 거리 1로 발견합니다.','같은 깊이에 있는 두 정점이 큐에 들어갑니다.','distance[B]=distance[C]=1'),
                       graph_scene([('A',55,130),('B',245,55),('C',245,220),('D',485,130)],[('A','B'),('A','C'),('B','D'),('C','D')],('D',),'D를 거리 2로 발견합니다.','B와 C 모두 D로 이어지지만 한 번만 기록합니다.','distance[D]=2')]),
    dict(
        id='backtracking-subsets', title='백트래킹 · 부분 집합', group='알고리즘', priority=2, difficulty='입문',
        summary='각 원소를 선택하거나 건너뛰며 가능한 부분 집합을 모두 만듭니다.',
        concept='원소마다 포함과 제외라는 두 갈래가 있습니다. 포함할 때 path에 값을 추가하고 재귀 호출이 돌아오면 pop으로 원상 복구합니다. 제외 갈래도 탐색하면 n개 원소의 부분 집합 2ⁿ개를 얻습니다. 이 단원은 각 집합 안에서 원래 순서를 유지하지만 결과 집합들의 순서는 자유입니다.',
        complexity='출력에 2ⁿ개 집합이 있어 최소 O(n·2ⁿ)의 출력 시간이 필요합니다. 경로 스택 O(n) 외에 결과 저장 O(n·2ⁿ)입니다.',
        application='작은 선택지 묶음에서 가능한 기능 조합을 빠짐없이 나열할 때 사용합니다.',
        questions=[('재귀 호출 뒤 path.pop이 필요한 이유는 무엇인가요?', '포함 갈래에서 넣은 값을 제거해야 다음 제외 갈래가 독립된 상태에서 시작한다.'),
                   ('n개 원소에는 부분 집합이 몇 개 있나요?', '각 원소를 넣거나 빼는 두 선택이 있어 2ⁿ개이며 빈 집합도 포함한다.')],
        requirements=['서로 다른 숫자가 담긴 `subsets(values: number[]): number[][]`를 구현하세요.',
                      '각 집합 안의 값은 입력 순서를 유지합니다. 집합 결과의 순서는 자유이며 빈 집합도 포함해야 합니다. 입력을 변경하지 마세요.'],
        starter='function subsets(values:number[]):number[][] { return []; }',
        reference='''function subsets(values:number[]):number[][] {
  const result:number[][]=[], path:number[]=[];
  function visit(index:number):void {
    if (index===values.length) { result.push([...path]); return; }
    path.push(values[index]); visit(index+1); path.pop();
    visit(index+1);
  }
  visit(0); return result;
}''',
        public_tests='''const result=subsets([1,2]).map(a=>a.join(',')).sort();
assertEqual(result,['','1','1,2','2'].sort());
assertEqual(subsets([]),[[]]);''',
        hidden_tests='''const values=[1,2,3]; const result=subsets(values);
assertEqual(result.length,8);
assertEqual(new Set(result.map(a=>a.join(','))).size,8);
assertEqual(result.map(a=>a.join(',')).sort(),['','1','2','3','1,2','1,3','2,3','1,2,3'].sort());
assertEqual(values,[1,2,3]);''',
        mutations=[('상태 복구', 'path.pop();', 'path.push(values[index]);'),
                   ('제외 갈래', 'visit(index+1);\n  }', 'return;\n  }')],
        visualization='backtracking-subsets', prerequisites=['dfs','array-rotation'],
        reading=guide('path는 현재 선택 갈래에 포함한 값만 담고, 재귀가 돌아오면 이전 상태로 복구됩니다.',
            [['포함 갈래로 간다','[1,2]에서 1과 2를 모두 선택해 [1,2]를 만듭니다.'],['선택을 되돌린다','2를 빼 [1] 상태로 돌아와 2를 제외한 집합을 만듭니다.'],['제외 갈래도 탐색','1을 빼고 [2]와 []를 만듭니다.']],
            'path 자체를 결과에 넣으면 나중에 pop한 내용이 이미 저장한 결과에도 반영될 수 있습니다. 복사본을 저장하세요.',
            '결과 개수 자체가 지수적으로 늘기 때문에 큰 입력에는 전체 나열이 적합하지 않습니다.',
            '몇 개의 기능 플래그 조합을 완전 탐색하며 테스트 입력을 생성할 수 있습니다.',
            '[1,2]에서 네 갈래를 순서대로 직접 적어보세요.'),
        hints=['빈 집합까지 포함해 2ⁿ개가 나오는지 확인하세요.', '하나의 갈래를 끝낸 뒤 선택 상태가 원래대로 돌아오는지 확인하세요.'],
        visual_frames=scenes(
            ([1,2],(0,),'1을 선택합니다.','현재 경로는 [1]입니다.','path.push(1)'),
            ([1,2],(0,1),'2도 선택합니다.','[1,2]를 결과에 복사해 저장합니다.','result.push([...path])'),
            ([1,2],(0,),'2를 빼고 돌아옵니다.','현재 경로를 [1]로 복구해 [1]도 저장합니다.','path.pop()'),
            ([1,2],(),'1도 제외한 갈래를 탐색합니다.','[2]와 []도 만들면 네 부분 집합이 완성됩니다.','2²=4'))),
    dict(
        id='dp-climb', title='동적 계획법 · 계단 경우의 수', group='알고리즘', priority=2, difficulty='입문',
        summary='작은 단계의 답을 재사용해 1칸·2칸 이동 경우의 수를 셉니다.',
        concept='n번째 계단에 마지막으로 오는 방법은 n-1에서 1칸 오거나 n-2에서 2칸 오는 두 경우뿐입니다. 따라서 ways(n)=ways(n-1)+ways(n-2)입니다. 0번째 계단에 서 있는 경우를 1가지로 놓으면 반복 계산 없이 앞으로 채울 수 있습니다.',
        complexity='n까지 한 번씩 계산하므로 시간 O(n), 직전 두 결과만 저장하면 추가 공간 O(1)입니다.',
        application='선택 폭이 작은 단계별 경로 수를 계산하는 DP의 첫 예시입니다.',
        questions=[('ways(n)이 직전 두 값의 합인 이유는 무엇인가요?', '마지막 이동이 1칸 또는 2칸인 경우가 서로 겹치지 않고 전체 경우를 이룬다.'),
                   ('ways(0)을 1로 두는 이유는 무엇인가요?', '아무 이동도 하지 않은 한 가지 방법이 있어 점화식의 시작값이 된다.')],
        requirements=['`climbWays(n: number): number`를 구현하세요.', '0≤n≤40이며 한 번에 1칸 또는 2칸 이동합니다. ways(0)=1입니다.'],
        starter='function climbWays(n:number):number { return 0; }',
        reference='''function climbWays(n:number):number {
  if (n<=1) return 1;
  let before=1, current=1;
  for (let step=2;step<=n;step++) [before,current]=[current,before+current];
  return current;
}''',
        public_tests='assertEqual(climbWays(0),1); assertEqual(climbWays(4),5);',
        hidden_tests='assertEqual(climbWays(1),1); assertEqual(climbWays(2),2); assertEqual(climbWays(5),8); assertEqual(climbWays(10),89); assertEqual(climbWays(40),165580141);',
        mutations=[('첫 단계', 'if (n<=1) return 1;', 'if (n<=1) return 0;'),
                   ('점화식', 'before+current', 'before+before')],
        visualization='dp-climb', prerequisites=['gcd'],
        reading=guide('before와 current는 각각 바로 전 두 계단의 경우의 수입니다.',
            [['시작값을 놓는다','ways(0)=1, ways(1)=1로 시작합니다.'],['두 경로를 합친다','ways(2)=1+1=2입니다.'],['앞으로 옮겨간다','ways(3)=ways(2)+ways(1)=3, ways(4)=5입니다.']],
            'n=0을 0가지로 두면 이후 결과가 틀립니다. 단순 재귀는 같은 하위 문제를 반복 계산합니다.',
            '직전 두 값만 필요하므로 전체 표를 저장할 필요는 없습니다.',
            '단계별 선택 경로 수를 계산할 때 하위 답을 재사용합니다.',
            '0부터 5까지 작은 표를 직접 작성해 점화식을 확인하세요.'),
        hints=['0·1·2의 초기값을 확인하세요.', 'n=5 이상의 값에서 앞선 두 결과를 올바르게 더하는지 확인하세요.'],
        visual_frames=scenes(
            ([1,1],(0,1),'0칸과 1칸의 경우의 수는 1입니다.','0칸은 아무 이동도 하지 않는 한 가지 방법입니다.','ways(0)=1; ways(1)=1'),
            ([1,1,2],(2,),'2칸에는 두 가지 방법이 있습니다.','1+1 또는 2로 이동합니다.','ways(2)=1+1=2'),
            ([1,1,2,3,5],(4,),'4칸의 경우는 5가지입니다.','3칸에서 1칸, 2칸에서 2칸 오는 방법을 합칩니다.','ways(4)=3+2=5'))),
])
