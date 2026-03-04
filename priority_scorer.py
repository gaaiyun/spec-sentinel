"""
优先级评分模块 - Priority Scorer
功能：RICE 评分、Kano 模型、价值/effort 矩阵
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum


class KanoCategory(Enum):
    """Kano 模型分类"""
    MUST_BE = "Must-be"  # 基本型需求
    PERFORMANCE = "Performance"  # 期望型需求
    DELIGHTER = "Delighter"  # 兴奋型需求
    INDIFFERENT = "Indifferent"  # 无差异需求
    REVERSE = "Reverse"  # 反向需求


class PriorityScorer:
    """优先级评分器 - 支持多种评分模型"""
    
    def __init__(self, requirements_df: pd.DataFrame):
        """
        初始化评分器
        
        Args:
            requirements_df: 需求数据框，必须包含 id 列
        """
        self.df = requirements_df.copy()
        
        # 确保有 id 列
        if 'id' not in self.df.columns:
            self.df['id'] = range(len(self.df))
        
        # 初始化评分列
        self._init_score_columns()
    
    def _init_score_columns(self):
        """初始化评分相关列"""
        score_columns = [
            'reach', 'impact', 'confidence', 'effort',  # RICE
            'rice_score',
            'kano_category', 'kano_score',
            'value_score', 'effort_score', 'value_effort_ratio',
            'priority_score', 'priority_rank'
        ]
        
        for col in score_columns:
            if col not in self.df.columns:
                self.df[col] = 0.0
    
    def calculate_rice_score(
        self,
        reach: Optional[pd.Series] = None,
        impact: Optional[pd.Series] = None,
        confidence: Optional[pd.Series] = None,
        effort: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        计算 RICE 评分
        
        RICE = (Reach × Impact × Confidence) / Effort
        
        Args:
            reach: 影响用户数（或频率）
            impact: 影响程度 (0.25-3)
            confidence: 信心指数 (0-100%)
            effort: 工作量（人周）
        """
        df = self.df
        
        # 使用提供的数据或现有列
        r = reach if reach is not None else df.get('reach', pd.Series([1000] * len(df)))
        i = impact if impact is not None else df.get('impact', pd.Series([1.0] * len(df)))
        c = confidence if confidence is not None else df.get('confidence', pd.Series([50] * len(df)))
        e = effort if effort is not None else df.get('effort', pd.Series([10] * len(df)))
        
        # 确保 effort 不为 0
        e = e.replace(0, 0.1)
        
        # 计算 RICE 分数
        rice_score = (r * i * (c / 100)) / e
        
        df['reach'] = r
        df['impact'] = i
        df['confidence'] = c
        df['effort'] = e
        df['rice_score'] = rice_score
        
        self.df = df
        return df
    
    def calculate_kano_score(
        self,
        functional_score: pd.Series,
        dysfunctional_score: pd.Series
    ) -> pd.DataFrame:
        """
        计算 Kano 模型评分
        
        Args:
            functional_score: 功能具备时的满意度 (1-5)
            dysfunctional_score: 功能缺失时的满意度 (1-5)
        """
        df = self.df
        
        # Kano 评估矩阵
        kano_map = {
            (5, 1): KanoCategory.MUST_BE,      # 必须有
            (5, 2): KanoCategory.MUST_BE,
            (4, 1): KanoCategory.MUST_BE,
            (4, 2): KanoCategory.MUST_BE,
            (5, 5): KanoCategory.INDIFFERENT,  # 无差异
            (4, 4): KanoCategory.INDIFFERENT,
            (3, 3): KanoCategory.INDIFFERENT,
            (5, 3): KanoCategory.PERFORMANCE,  # 期望型
            (5, 4): KanoCategory.PERFORMANCE,
            (4, 3): KanoCategory.PERFORMANCE,
            (4, 5): KanoCategory.DELIGHTER,    # 兴奋型
            (3, 5): KanoCategory.DELIGHTER,
            (2, 5): KanoCategory.DELIGHTER,
            (1, 5): KanoCategory.REVERSE,      # 反向
            (1, 4): KanoCategory.REVERSE,
            (2, 4): KanoCategory.REVERSE,
        }
        
        # 默认映射
        default_category = KanoCategory.PERFORMANCE
        
        kano_categories = []
        kano_scores = []
        
        for f, d in zip(functional_score, dysfunctional_score):
            f, d = int(round(f)), int(round(d))
            category = kano_map.get((f, d), default_category)
            kano_categories.append(category.value)
            
            # Kano 分数
            score_map = {
                KanoCategory.MUST_BE: 0.8,
                KanoCategory.PERFORMANCE: 0.6,
                KanoCategory.DELIGHTER: 0.4,
                KanoCategory.INDIFFERENT: 0.2,
                KanoCategory.REVERSE: 0.1
            }
            kano_scores.append(score_map[category])
        
        df['functional_score'] = functional_score
        df['dysfunctional_score'] = dysfunctional_score
        df['kano_category'] = kano_categories
        df['kano_score'] = kano_scores
        
        self.df = df
        return df
    
    def calculate_value_effort_matrix(
        self,
        value: Optional[pd.Series] = None,
        effort: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        计算价值/努力矩阵
        
        Args:
            value: 业务价值 (1-10)
            effort: 实现难度 (1-10)
        """
        df = self.df
        
        v = value if value is not None else df.get('value_score', pd.Series([5] * len(df)))
        e = effort if effort is not None else df.get('effort_score', pd.Series([5] * len(df)))
        
        # 避免除零
        e = e.replace(0, 0.1)
        
        df['value_score'] = v
        df['effort_score'] = e
        df['value_effort_ratio'] = v / e
        
        #  quadrant 分类
        quadrants = []
        for val, eff in zip(v, e):
            if val >= 5 and eff <= 5:
                quadrants.append('Quick Win')  # 高价值低努力
            elif val >= 5 and eff > 5:
                quadrants.append('Major Project')  # 高价值高努力
            elif val < 5 and eff <= 5:
                quadrants.append('Fill-in')  # 低价值低努力
            else:
                quadrants.append('Thankless Task')  # 低价值高努力
        
        df['quadrant'] = quadrants
        
        self.df = df
        return df
    
    def calculate_combined_priority(
        self,
        weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        计算综合优先级分数
        
        Args:
            weights: 各评分模型的权重
                - rice_weight: RICE 权重 (默认 0.4)
                - kano_weight: Kano 权重 (默认 0.3)
                - ve_weight: 价值努力权重 (默认 0.3)
        """
        df = self.df
        
        if weights is None:
            weights = {'rice_weight': 0.4, 'kano_weight': 0.3, 've_weight': 0.3}
        
        # 归一化各分数
        def normalize(series):
            min_val, max_val = series.min(), series.max()
            if max_val - min_val == 0:
                return pd.Series([0.5] * len(series))
            return (series - min_val) / (max_val - min_val)
        
        rice_norm = normalize(df['rice_score']) if 'rice_score' in df.columns else pd.Series([0.5] * len(df))
        kano_norm = normalize(df['kano_score']) if 'kano_score' in df.columns else pd.Series([0.5] * len(df))
        ve_norm = normalize(df['value_effort_ratio']) if 'value_effort_ratio' in df.columns else pd.Series([0.5] * len(df))
        
        # 综合分数
        priority_score = (
            weights['rice_weight'] * rice_norm +
            weights['kano_weight'] * kano_norm +
            weights['ve_weight'] * ve_norm
        )
        
        df['priority_score'] = priority_score * 100  # 转换为 0-100 分
        df['priority_rank'] = df['priority_score'].rank(ascending=False).astype(int)
        
        self.df = df
        return df
    
    def get_priority_matrix(self) -> pd.DataFrame:
        """获取优先级矩阵（用于可视化）"""
        df = self.df
        
        matrix = df[['id', 'title', 'value_score', 'effort_score', 'quadrant', 'priority_rank']].copy()
        return matrix
    
    def get_top_priorities(self, n: int = 10) -> pd.DataFrame:
        """获取前 N 个高优先级需求"""
        return self.df.nlargest(n, 'priority_score')
    
    def get_by_quadrant(self, quadrant: str) -> pd.DataFrame:
        """获取特定象限的需求"""
        return self.df[self.df['quadrant'] == quadrant]
    
    def export_scores(self) -> pd.DataFrame:
        """导出评分结果"""
        score_cols = [
            'id', 'title', 'category',
            'reach', 'impact', 'confidence', 'effort', 'rice_score',
            'kano_category', 'kano_score',
            'value_score', 'effort_score', 'value_effort_ratio', 'quadrant',
            'priority_score', 'priority_rank'
        ]
        
        available_cols = [col for col in score_cols if col in self.df.columns]
        return self.df[available_cols]


def create_sample_scores(requirements_df: pd.DataFrame) -> pd.DataFrame:
    """为示例数据创建评分"""
    scorer = PriorityScorer(requirements_df)
    
    # 示例 RICE 数据
    np.random.seed(42)
    n = len(requirements_df)
    
    reach = pd.Series(np.random.randint(100, 10000, n))
    impact = pd.Series(np.random.uniform(0.5, 3.0, n))
    confidence = pd.Series(np.random.randint(40, 100, n))
    effort = pd.Series(np.random.randint(2, 20, n))
    
    # 计算 RICE
    scorer.calculate_rice_score(reach, impact, confidence, effort)
    
    # 示例 Kano 数据
    functional = pd.Series(np.random.randint(3, 6, n))
    dysfunctional = pd.Series(np.random.randint(1, 4, n))
    scorer.calculate_kano_score(functional, dysfunctional)
    
    # 价值/努力矩阵
    value = pd.Series(np.random.randint(3, 10, n))
    effort_score = pd.Series(np.random.randint(2, 10, n))
    scorer.calculate_value_effort_matrix(value, effort_score)
    
    # 综合优先级
    scorer.calculate_combined_priority()
    
    return scorer.df


if __name__ == '__main__':
    # 测试代码
    from requirement_analyzer import create_sample_requirements, RequirementAnalyzer
    
    analyzer = RequirementAnalyzer()
    df = analyzer.import_from_dict(create_sample_requirements())
    df = analyzer.classify_all()
    
    scored_df = create_sample_scores(df)
    print(scored_df[['title', 'rice_score', 'priority_score', 'priority_rank']])
