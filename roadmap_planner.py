"""
路线图规划模块 - Roadmap Planner
功能：时间线可视化、依赖关系管理
"""

import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json


class RoadmapPlanner:
    """路线图规划器 - 时间线和依赖关系管理"""
    
    def __init__(self):
        self.requirements_df = None
        self.dependency_graph = nx.DiGraph()
        self.timeline_data = None
        self.milestones = []
    
    def load_requirements(self, requirements_df: pd.DataFrame) -> None:
        """
        加载需求数据
        
        Args:
            requirements_df: 需求数据框，必须包含 id, title, effort 等列
        """
        self.requirements_df = requirements_df.copy()
        
        # 确保有必需列
        required_cols = ['id', 'title']
        for col in required_cols:
            if col not in self.requirements_df.columns:
                raise Exception(f"缺少必需列：{col}")
        
        # 初始化默认列
        if 'effort' not in self.requirements_df.columns:
            self.requirements_df['effort'] = 5  # 默认 5 周
        if 'priority_rank' not in self.requirements_df.columns:
            self.requirements_df['priority_rank'] = range(1, len(self.requirements_df) + 1)
        if 'status' not in self.requirements_df.columns:
            self.requirements_df['status'] = 'planned'
    
    def add_dependency(self, from_id: int, to_id: int, dependency_type: str = 'FS') -> None:
        """
        添加依赖关系
        
        Args:
            from_id: 前置需求 ID
            to_id: 后置需求 ID
            dependency_type: 依赖类型
                - FS: Finish-to-Start (完成后开始)
                - SS: Start-to-Start (同时开始)
                - FF: Finish-to-Finish (同时完成)
                - SF: Start-to-Finish (开始后完成)
        """
        self.dependency_graph.add_edge(from_id, to_id, type=dependency_type)
    
    def add_dependencies_from_list(self, dependencies: List[Tuple[int, int, str]]) -> None:
        """批量添加依赖关系"""
        for from_id, to_id, dep_type in dependencies:
            self.add_dependency(from_id, to_id, dep_type)
    
    def detect_cycles(self) -> List[List[int]]:
        """检测依赖环"""
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            return cycles
        except:
            return []
    
    def get_critical_path(self) -> List[int]:
        """获取关键路径（最长路径）"""
        if not self.dependency_graph.nodes():
            return []
        
        try:
            # 找到所有源节点（没有前置的）
            source_nodes = [n for n in self.dependency_graph.nodes() 
                          if self.dependency_graph.in_degree(n) == 0]
            
            if not source_nodes:
                return []
            
            # 找到所有汇节点（没有后置的）
            sink_nodes = [n for n in self.dependency_graph.nodes() 
                         if self.dependency_graph.out_degree(n) == 0]
            
            # 计算最长路径
            longest_path = []
            for source in source_nodes:
                for sink in sink_nodes:
                    try:
                        path = nx.dag_longest_path(self.dependency_graph)
                        if len(path) > len(longest_path):
                            longest_path = path
                    except:
                        continue
            
            return longest_path
        except:
            return []
    
    def schedule_timeline(
        self,
        start_date: datetime = None,
        team_capacity: int = 2,
        max_parallel: int = 3
    ) -> pd.DataFrame:
        """
        安排时间线
        
        Args:
            start_date: 开始日期
            team_capacity: 团队容量（人）
            max_parallel: 最大并行任务数
        """
        if self.requirements_df is None:
            raise Exception("请先加载需求数据")
        
        if start_date is None:
            start_date = datetime.now()
        
        df = self.requirements_df.copy()
        
        # 按优先级排序
        df = df.sort_values('priority_rank')
        
        # 计算开始和结束时间
        scheduled = []
        current_date = start_date
        active_tasks = []
        resource_load = 0
        
        for _, row in df.iterrows():
            req_id = row['id']
            effort = row.get('effort', 5)
            
            # 检查依赖
            deps = list(self.dependency_graph.predecessors(req_id))
            if deps:
                # 等待所有前置任务完成
                max_end = max(
                    [s['end_date'] for s in scheduled if s['id'] in deps],
                    default=current_date
                )
                start = max(max_end, current_date)
            else:
                start = current_date
            
            # 考虑资源限制
            end_date = start + timedelta(weeks=effort / team_capacity)
            
            scheduled.append({
                'id': req_id,
                'title': row['title'],
                'start_date': start,
                'end_date': end_date,
                'effort': effort,
                'priority_rank': row.get('priority_rank', 999),
                'status': row.get('status', 'planned'),
                'category': row.get('category', 'General')
            })
            
            # 更新当前日期（简化：顺序执行）
            current_date = end_date
        
        self.timeline_data = pd.DataFrame(scheduled)
        return self.timeline_data
    
    def add_milestone(
        self,
        name: str,
        date: datetime,
        description: str = '',
        linked_requirements: List[int] = None
    ) -> None:
        """添加里程碑"""
        self.milestones.append({
            'name': name,
            'date': date,
            'description': description,
            'linked_requirements': linked_requirements or []
        })
    
    def get_quarterly_plan(self, quarters: int = 4) -> pd.DataFrame:
        """
        生成季度计划
        
        Args:
            quarters: 计划季度数
        """
        if self.timeline_data is None:
            self.schedule_timeline()
        
        df = self.timeline_data.copy()
        
        # 添加季度列
        if len(df) > 0:
            start_quarter = df['start_date'].min()
            df['quarter'] = df['start_date'].apply(
                lambda d: f"Q{(d - start_quarter).days // 90 + 1}"
            )
            
            # 按季度汇总
            quarterly = df.groupby('quarter').agg({
                'id': 'count',
                'effort': 'sum',
                'title': lambda x: '|'.join(x.tolist()[:5])  # 前 5 个任务
            }).reset_index()
            quarterly.columns = ['quarter', 'task_count', 'total_effort', 'key_tasks']
        
        return quarterly
    
    def get_resource_allocation(self) -> pd.DataFrame:
        """获取资源分配情况"""
        if self.timeline_data is None:
            raise Exception("请先安排时间线")
        
        df = self.timeline_data.copy()
        
        # 按周统计工作量
        df['week'] = df['start_date'].apply(
            lambda d: d.isocalendar()[1]
        )
        
        weekly = df.groupby('week').agg({
            'effort': 'sum',
            'id': 'count'
        }).reset_index()
        weekly.columns = ['week', 'total_effort', 'task_count']
        
        return weekly
    
    def detect_bottlenecks(self, threshold_weeks: float = 4) -> List[Dict]:
        """
        检测瓶颈任务
        
        Args:
            threshold_weeks: 瓶颈阈值（周）
        """
        if self.timeline_data is None:
            raise Exception("请先安排时间线")
        
        bottlenecks = []
        
        # 查找耗时长的任务
        long_tasks = self.timeline_data[
            self.timeline_data['effort'] >= threshold_weeks
        ]
        
        for _, row in long_tasks.iterrows():
            bottlenecks.append({
                'id': row['id'],
                'title': row['title'],
                'effort': row['effort'],
                'reason': '高工作量任务'
            })
        
        # 查找依赖多的任务
        for node in self.dependency_graph.nodes():
            in_degree = self.dependency_graph.in_degree(node)
            out_degree = self.dependency_graph.out_degree(node)
            
            if in_degree >= 3 or out_degree >= 3:
                bottlenecks.append({
                    'id': node,
                    'title': self.timeline_data[
                        self.timeline_data['id'] == node
                    ]['title'].values[0] if len(self.timeline_data) > 0 else 'Unknown',
                    'dependencies': in_degree + out_degree,
                    'reason': '高依赖任务'
                })
        
        return bottlenecks
    
    def export_to_json(self, file_path: str) -> None:
        """导出路线图到 JSON"""
        data = {
            'timeline': [],
            'milestones': self.milestones,
            'dependencies': []
        }
        
        if self.timeline_data is not None:
            df = self.timeline_data.copy()
            df['start_date'] = df['start_date'].astype(str)
            df['end_date'] = df['end_date'].astype(str)
            data['timeline'] = df.to_dict('records')
        
        for edge in self.dependency_graph.edges(data=True):
            data['dependencies'].append({
                'from': edge[0],
                'to': edge[1],
                'type': edge[2].get('type', 'FS')
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_gantt_data(self) -> List[Dict]:
        """获取甘特图数据"""
        if self.timeline_data is None:
            return []
        
        gantt_data = []
        for _, row in self.timeline_data.iterrows():
            gantt_data.append({
                'Task': row['title'],
                'Start': row['start_date'],
                'Finish': row['end_date'],
                'Resource': row.get('category', 'General'),
                'Priority': row.get('priority_rank', 50)
            })
        
        return gantt_data


def create_sample_dependencies(requirements_df: pd.DataFrame) -> List[Tuple[int, int, str]]:
    """创建示例依赖关系"""
    dependencies = []
    
    # 假设有基础功能 -> 高级功能的依赖
    ids = requirements_df['id'].tolist() if 'id' in requirements_df.columns else list(range(1, len(requirements_df) + 1))
    
    if len(ids) >= 4:
        # 基础功能依赖
        dependencies.append((ids[0], ids[2], 'FS'))  # 需求 1 -> 需求 3
        dependencies.append((ids[1], ids[3], 'FS'))  # 需求 2 -> 需求 4
        
        if len(ids) >= 6:
            dependencies.append((ids[2], ids[4], 'FS'))  # 需求 3 -> 需求 5
            dependencies.append((ids[3], ids[5], 'FS'))  # 需求 4 -> 需求 6
    
    return dependencies


if __name__ == '__main__':
    # 测试代码
    from datetime import datetime, timedelta
    import pandas as pd
    
    # 创建示例数据
    data = {
        'id': [1, 2, 3, 4, 5, 6],
        'title': ['需求 A', '需求 B', '需求 C', '需求 D', '需求 E', '需求 F'],
        'effort': [3, 5, 4, 6, 3, 5],
        'priority_rank': [1, 2, 3, 4, 5, 6],
        'category': ['功能', '功能', '体验', '性能', '安全', '功能']
    }
    df = pd.DataFrame(data)
    
    planner = RoadmapPlanner()
    planner.load_requirements(df)
    
    # 添加依赖
    deps = create_sample_dependencies(df)
    planner.add_dependencies_from_list(deps)
    
    # 检测环
    cycles = planner.detect_cycles()
    print(f"依赖环：{cycles}")
    
    # 安排时间线
    timeline = planner.schedule_timeline(
        start_date=datetime.now(),
        team_capacity=2
    )
    print("\n时间线:")
    print(timeline[['title', 'start_date', 'end_date', 'effort']])
    
    # 获取关键路径
    critical_path = planner.get_critical_path()
    print(f"\n关键路径：{critical_path}")
    
    # 季度计划
    quarterly = planner.get_quarterly_plan()
    print("\n季度计划:")
    print(quarterly)
