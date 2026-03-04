"""
竞品分析模块 - Competitor Analyzer
功能：竞品功能对比、差距分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json


class CompetitorAnalyzer:
    """竞品分析器 - 功能对比和差距分析"""
    
    def __init__(self):
        self.competitors_df = None
        self.features_df = None
        self.comparison_matrix = None
    
    def add_competitor(self, name: str, info: Dict) -> None:
        """
        添加竞品信息
        
        Args:
            name: 竞品名称
            info: 竞品信息字典，包含：
                - company: 公司名称
                - market_share: 市场份额 (%)
                - pricing: 价格策略
                - target_users: 目标用户
                - strengths: 优势列表
                - weaknesses: 劣势列表
        """
        if self.competitors_df is None:
            self.competitors_df = pd.DataFrame(columns=[
                'name', 'company', 'market_share', 'pricing', 
                'target_users', 'strengths', 'weaknesses'
            ])
        
        competitor = {
            'name': name,
            'company': info.get('company', ''),
            'market_share': info.get('market_share', 0),
            'pricing': info.get('pricing', ''),
            'target_users': info.get('target_users', ''),
            'strengths': '|'.join(info.get('strengths', [])),
            'weaknesses': '|'.join(info.get('weaknesses', []))
        }
        
        self.competitors_df = pd.concat([
            self.competitors_df,
            pd.DataFrame([competitor])
        ], ignore_index=True)
    
    def add_features(self, features: List[Dict]) -> None:
        """
        添加功能对比数据
        
        Args:
            features: 功能列表，每个功能包含：
                - feature_name: 功能名称
                - category: 功能类别
                - our_product: 是否具备 (0-5 分)
                - competitor_scores: {competitor_name: score}
        """
        records = []
        for feat in features:
            record = {
                'feature_name': feat['feature_name'],
                'category': feat.get('category', 'General'),
                'our_score': feat.get('our_product', 0)
            }
            
            # 添加各竞品得分
            for comp_name, score in feat.get('competitor_scores', {}).items():
                record[f'{comp_name}_score'] = score
            
            records.append(record)
        
        self.features_df = pd.DataFrame(records)
    
    def create_comparison_matrix(self) -> pd.DataFrame:
        """创建功能对比矩阵"""
        if self.features_df is None:
            raise Exception("请先添加功能数据")
        
        # 提取所有竞品列
        score_cols = [col for col in self.features_df.columns if col.endswith('_score')]
        
        # 创建对比矩阵
        self.comparison_matrix = self.features_df[['feature_name', 'category', 'our_score'] + score_cols].copy()
        
        # 计算差距
        for col in score_cols:
            if col != 'our_score':
                diff_col = col.replace('_score', '_gap')
                self.comparison_matrix[diff_col] = self.comparison_matrix[col] - self.comparison_matrix['our_score']
        
        # 计算平均得分
        competitor_cols = [col for col in score_cols if col != 'our_score']
        if competitor_cols:
            self.comparison_matrix['competitor_avg'] = self.comparison_matrix[competitor_cols].mean(axis=1)
            self.comparison_matrix['overall_gap'] = self.comparison_matrix['competitor_avg'] - self.comparison_matrix['our_score']
        
        return self.comparison_matrix
    
    def get_gap_analysis(self) -> pd.DataFrame:
        """获取差距分析结果"""
        if self.comparison_matrix is None:
            self.create_comparison_matrix()
        
        gap_cols = [col for col in self.comparison_matrix.columns if col.endswith('_gap')]
        
        if not gap_cols:
            return pd.DataFrame()
        
        gap_analysis = self.comparison_matrix[['feature_name', 'category', 'our_score'] + gap_cols].copy()
        
        # 按总体差距排序
        if 'overall_gap' in gap_analysis.columns:
            gap_analysis = gap_analysis.sort_values('overall_gap', ascending=False)
        
        return gap_analysis
    
    def get_priority_gaps(self, threshold: float = 1.0) -> pd.DataFrame:
        """
        获取需要优先追赶的功能差距
        
        Args:
            threshold: 差距阈值，超过此值的功能需要优先处理
        """
        if self.comparison_matrix is None:
            self.create_comparison_matrix()
        
        if 'overall_gap' not in self.comparison_matrix.columns:
            return pd.DataFrame()
        
        priority_gaps = self.comparison_matrix[
            self.comparison_matrix['overall_gap'] >= threshold
        ][['feature_name', 'category', 'our_score', 'competitor_avg', 'overall_gap']].copy()
        
        priority_gaps = priority_gaps.sort_values('overall_gap', ascending=False)
        
        return priority_gaps
    
    def get_competitive_advantages(self) -> pd.DataFrame:
        """获取我们的竞争优势功能"""
        if self.comparison_matrix is None:
            self.create_comparison_matrix()
        
        if 'overall_gap' not in self.comparison_matrix.columns:
            return pd.DataFrame()
        
        advantages = self.comparison_matrix[
            self.comparison_matrix['overall_gap'] < 0
        ][['feature_name', 'category', 'our_score', 'competitor_avg', 'overall_gap']].copy()
        
        advantages = advantages.sort_values('overall_gap', ascending=True)
        
        return advantages
    
    def get_category_summary(self) -> pd.DataFrame:
        """获取各功能类别的对比汇总"""
        if self.comparison_matrix is None:
            self.create_comparison_matrix()
        
        summary = self.comparison_matrix.groupby('category').agg({
            'our_score': 'mean',
            'competitor_avg': 'mean' if 'competitor_avg' in self.comparison_matrix.columns else 'mean',
            'overall_gap': 'mean' if 'overall_gap' in self.comparison_matrix.columns else 'mean',
            'feature_name': 'count'
        }).reset_index()
        
        summary.columns = ['category', 'our_avg_score', 'competitor_avg_score', 'avg_gap', 'feature_count']
        
        return summary
    
    def calculate_feature_importance(
        self,
        importance_scores: Dict[str, float]
    ) -> pd.DataFrame:
        """
        计算功能重要性加权分析
        
        Args:
            importance_scores: 功能重要性评分 {feature_name: importance}
        """
        if self.comparison_matrix is None:
            self.create_comparison_matrix()
        
        df = self.comparison_matrix.copy()
        
        # 添加重要性评分
        df['importance'] = df['feature_name'].map(importance_scores).fillna(5.0)
        
        # 计算加权差距
        if 'overall_gap' in df.columns:
            df['weighted_gap'] = df['overall_gap'] * df['importance']
        
        # 按加权差距排序
        if 'weighted_gap' in df.columns:
            df = df.sort_values('weighted_gap', ascending=False)
        
        return df
    
    def generate_swot_analysis(self) -> Dict:
        """生成 SWOT 分析"""
        if self.competitors_df is None:
            raise Exception("请先添加竞品信息")
        
        swot = {
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'threats': []
        }
        
        # 分析我们的优势
        if self.comparison_matrix is not None:
            advantages = self.get_competitive_advantages()
            for _, row in advantages.head(5).iterrows():
                swot['strengths'].append(f"功能 '{row['feature_name']}' 领先竞品 {abs(row['overall_gap']):.1f} 分")
        
        # 分析我们的劣势
        if self.comparison_matrix is not None:
            gaps = self.get_priority_gaps()
            for _, row in gaps.head(5).iterrows():
                swot['weaknesses'].append(f"功能 '{row['feature_name']}' 落后竞品 {row['overall_gap']:.1f} 分")
        
        # 市场机会
        if self.competitors_df is not None:
            for _, comp in self.competitors_df.iterrows():
                if comp['market_share'] < 20:  # 市场份额较小的竞品
                    swot['opportunities'].append(f"可从 {comp['name']} ({comp['market_share']}% 份额) 争取用户")
                weaknesses = comp['weaknesses'].split('|') if comp['weaknesses'] else []
                for w in weaknesses[:2]:
                    if w.strip():
                        swot['opportunities'].append(f"针对 {comp['name']} 的弱点：{w}")
        
        # 市场威胁
        if self.competitors_df is not None:
            top_competitors = self.competitors_df.nlargest(2, 'market_share')
            for _, comp in top_competitors.iterrows():
                swot['threats'].append(f"{comp['name']} 占据 {comp['market_share']}% 市场份额")
                strengths = comp['strengths'].split('|') if comp['strengths'] else []
                for s in strengths[:2]:
                    if s.strip():
                        swot['threats'].append(f"{comp['name']} 优势：{s}")
        
        return swot
    
    def export_analysis(self, file_path: str) -> None:
        """导出分析结果到 JSON"""
        result = {
            'competitors': self.competitors_df.to_dict('records') if self.competitors_df is not None else [],
            'comparison_matrix': self.comparison_matrix.to_dict('records') if self.comparison_matrix is not None else [],
            'swot': self.generate_swot_analysis() if self.competitors_df is not None else {}
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)


def create_sample_competitor_data() -> Tuple[List[Dict], List[Dict]]:
    """创建示例竞品和功能数据"""
    
    # 竞品信息
    competitors = [
        {
            'name': '竞品 A',
            'info': {
                'company': '公司 A',
                'market_share': 35,
                'pricing': '高端定价',
                'target_users': '企业用户',
                'strengths': ['品牌知名度高', '功能完善', '服务好'],
                'weaknesses': ['价格高', '学习曲线陡峭']
            }
        },
        {
            'name': '竞品 B',
            'info': {
                'company': '公司 B',
                'market_share': 25,
                'pricing': '中端定价',
                'target_users': '中小企业',
                'strengths': ['性价比高', '易用性好'],
                'weaknesses': ['功能较少', '扩展性差']
            }
        },
        {
            'name': '竞品 C',
            'info': {
                'company': '公司 C',
                'market_share': 15,
                'pricing': '低端定价',
                'target_users': '个人用户',
                'strengths': ['免费版本', '界面简洁'],
                'weaknesses': ['功能基础', '广告多']
            }
        }
    ]
    
    # 功能对比数据
    features = [
        {
            'feature_name': '数据导入',
            'category': '核心功能',
            'our_product': 4,
            'competitor_scores': {'竞品 A': 5, '竞品 B': 4, '竞品 C': 3}
        },
        {
            'feature_name': '数据分析',
            'category': '核心功能',
            'our_product': 5,
            'competitor_scores': {'竞品 A': 5, '竞品 B': 3, '竞品 C': 2}
        },
        {
            'feature_name': '报告导出',
            'category': '核心功能',
            'our_product': 4,
            'competitor_scores': {'竞品 A': 5, '竞品 B': 4, '竞品 C': 3}
        },
        {
            'feature_name': '用户界面',
            'category': '用户体验',
            'our_product': 4,
            'competitor_scores': {'竞品 A': 4, '竞品 B': 5, '竞品 C': 4}
        },
        {
            'feature_name': '移动端支持',
            'category': '用户体验',
            'our_product': 3,
            'competitor_scores': {'竞品 A': 4, '竞品 B': 4, '竞品 C': 3}
        },
        {
            'feature_name': 'API 集成',
            'category': '扩展能力',
            'our_product': 4,
            'competitor_scores': {'竞品 A': 5, '竞品 B': 3, '竞品 C': 2}
        },
        {
            'feature_name': '自定义报表',
            'category': '扩展能力',
            'our_product': 3,
            'competitor_scores': {'竞品 A': 5, '竞品 B': 4, '竞品 C': 2}
        },
        {
            'feature_name': '团队协作',
            'category': '扩展能力',
            'our_product': 4,
            'competitor_scores': {'竞品 A': 5, '竞品 B': 4, '竞品 C': 2}
        },
        {
            'feature_name': '数据安全',
            'category': '安全性',
            'our_product': 5,
            'competitor_scores': {'竞品 A': 5, '竞品 B': 4, '竞品 C': 3}
        },
        {
            'feature_name': '客户支持',
            'category': '服务',
            'our_product': 4,
            'competitor_scores': {'竞品 A': 5, '竞品 B': 4, '竞品 C': 2}
        }
    ]
    
    return competitors, features


if __name__ == '__main__':
    # 测试代码
    analyzer = CompetitorAnalyzer()
    
    competitors, features = create_sample_competitor_data()
    
    # 添加竞品
    for comp in competitors:
        analyzer.add_competitor(comp['name'], comp['info'])
    
    # 添加功能
    analyzer.add_features(features)
    
    # 创建对比矩阵
    matrix = analyzer.create_comparison_matrix()
    print("功能对比矩阵:")
    print(matrix[['feature_name', 'our_score', 'competitor_avg', 'overall_gap']])
    
    # 差距分析
    print("\n优先追赶的功能:")
    print(analyzer.get_priority_gaps(threshold=0.5))
