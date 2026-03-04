"""
需求分析模块 - Requirement Analyzer
功能：需求导入、分类、清洗和预处理
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from typing import Dict, List, Optional, Tuple
import re


class RequirementAnalyzer:
    """需求分析器 - 支持多渠道需求导入和自动分类"""
    
    # 需求分类关键词
    CATEGORY_KEYWORDS = {
        '功能': ['功能', '特性', '支持', '添加', '实现', '能够', '可以', 'module', 'feature', 'support'],
        '体验': ['体验', '界面', '交互', '美观', '流畅', '易用', '友好', 'ux', 'ui', 'design'],
        '性能': ['性能', '速度', '优化', '响应', '延迟', '并发', '效率', 'performance', 'speed', 'optimize'],
        '安全': ['安全', '权限', '加密', '保护', '隐私', '风险', '漏洞', 'security', 'encrypt', 'privacy']
    }
    
    def __init__(self):
        self.requirements_df = None
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.classifier = None
        
    def import_from_csv(self, file_path: str) -> pd.DataFrame:
        """从 CSV 导入需求"""
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            return self._validate_and_normalize(df)
        except Exception as e:
            raise Exception(f"CSV 导入失败：{str(e)}")
    
    def import_from_excel(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """从 Excel 导入需求"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            return self._validate_and_normalize(df)
        except Exception as e:
            raise Exception(f"Excel 导入失败：{str(e)}")
    
    def import_from_dict(self, requirements: List[Dict]) -> pd.DataFrame:
        """从字典列表导入需求"""
        df = pd.DataFrame(requirements)
        return self._validate_and_normalize(df)
    
    def _validate_and_normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证和标准化需求数据"""
        # 必需字段
        required_cols = ['id', 'title', 'description']
        
        # 检查必需字段
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''
        
        # 标准化字段
        df['id'] = df['id'].fillna(range(len(df)))
        df['title'] = df['title'].fillna('').astype(str)
        df['description'] = df['description'].fillna('').astype(str)
        
        # 添加默认字段
        if 'category' not in df.columns:
            df['category'] = ''
        if 'source' not in df.columns:
            df['source'] = 'unknown'
        if 'status' not in df.columns:
            df['status'] = 'pending'
        if 'created_date' not in df.columns:
            df['created_date'] = pd.Timestamp.now()
            
        self.requirements_df = df
        return df
    
    def auto_classify(self, text: str) -> str:
        """自动分类需求文本"""
        text_lower = text.lower()
        
        # 基于关键词的分类
        category_scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            category_scores[category] = score
        
        # 返回得分最高的类别
        if max(category_scores.values()) > 0:
            return max(category_scores, key=category_scores.get)
        
        return '功能'  # 默认类别
    
    def classify_all(self) -> pd.DataFrame:
        """对所有需求进行自动分类"""
        if self.requirements_df is None:
            raise Exception("请先导入需求数据")
        
        # 结合 title 和 description 进行分类
        texts = self.requirements_df['title'] + ' ' + self.requirements_df['description']
        self.requirements_df['auto_category'] = texts.apply(self.auto_classify)
        
        # 如果没有手动分类，使用自动分类
        mask = self.requirements_df['category'] == ''
        self.requirements_df.loc[mask, 'category'] = self.requirements_df.loc[mask, 'auto_category']
        
        return self.requirements_df
    
    def cluster_requirements(self, n_clusters: int = 5) -> pd.DataFrame:
        """使用聚类算法对需求进行分组"""
        if self.requirements_df is None:
            raise Exception("请先导入需求数据")
        
        texts = self.requirements_df['title'] + ' ' + self.requirements_df['description']
        
        # TF-IDF 向量化
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        
        # K-means 聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(tfidf_matrix)
        
        self.requirements_df['cluster'] = clusters
        
        return self.requirements_df
    
    def get_category_summary(self) -> pd.DataFrame:
        """获取需求分类统计"""
        if self.requirements_df is None:
            raise Exception("请先导入需求数据")
        
        summary = self.requirements_df.groupby('category').agg({
            'id': 'count',
            'title': lambda x: len(x)
        }).reset_index()
        summary.columns = ['category', 'count', 'count']
        
        return summary
    
    def get_requirements_by_category(self, category: str) -> pd.DataFrame:
        """获取特定类别的需求"""
        if self.requirements_df is None:
            raise Exception("请先导入需求数据")
        
        return self.requirements_df[self.requirements_df['category'] == category]
    
    def search_requirements(self, query: str) -> pd.DataFrame:
        """搜索需求"""
        if self.requirements_df is None:
            raise Exception("请先导入需求数据")
        
        query_lower = query.lower()
        mask = (
            self.requirements_df['title'].str.lower().str.contains(query_lower) |
            self.requirements_df['description'].str.lower().str.contains(query_lower)
        )
        
        return self.requirements_df[mask]
    
    def export_to_csv(self, file_path: str) -> None:
        """导出需求到 CSV"""
        if self.requirements_df is None:
            raise Exception("没有可导出的需求数据")
        
        self.requirements_df.to_csv(file_path, index=False, encoding='utf-8-sig')
    
    def get_statistics(self) -> Dict:
        """获取需求统计信息"""
        if self.requirements_df is None:
            raise Exception("请先导入需求数据")
        
        return {
            'total_count': len(self.requirements_df),
            'by_category': self.requirements_df['category'].value_counts().to_dict(),
            'by_status': self.requirements_df['status'].value_counts().to_dict(),
            'by_source': self.requirements_df['source'].value_counts().to_dict()
        }


def create_sample_requirements() -> List[Dict]:
    """创建示例需求数据"""
    return [
        {
            'id': 1,
            'title': '用户登录功能优化',
            'description': '优化用户登录流程，支持第三方登录（微信、QQ、Google），减少登录步骤，提升用户体验',
            'category': '体验',
            'source': '用户反馈',
            'status': 'pending'
        },
        {
            'id': 2,
            'title': '数据导出功能',
            'description': '支持将分析结果导出为 Excel、PDF、CSV 等多种格式，方便用户分享和存档',
            'category': '功能',
            'source': '产品规划',
            'status': 'pending'
        },
        {
            'id': 3,
            'title': '页面加载速度优化',
            'description': '优化前端资源加载，实现懒加载和缓存策略，将页面加载时间控制在 2 秒以内',
            'category': '性能',
            'source': '技术团队',
            'status': 'pending'
        },
        {
            'id': 4,
            'title': '数据加密存储',
            'description': '对用户敏感数据进行加密存储，包括密码、个人信息等，符合 GDPR 合规要求',
            'category': '安全',
            'source': '安全审计',
            'status': 'pending'
        },
        {
            'id': 5,
            'title': '智能推荐系统',
            'description': '基于用户行为数据，构建个性化推荐系统，提升用户粘性和转化率',
            'category': '功能',
            'source': '数据分析',
            'status': 'pending'
        },
        {
            'id': 6,
            'title': '移动端适配',
            'description': '优化移动端界面布局和交互体验，支持响应式设计，适配各种屏幕尺寸',
            'category': '体验',
            'source': '用户反馈',
            'status': 'pending'
        },
        {
            'id': 7,
            'title': 'API 限流机制',
            'description': '实现 API 请求限流和熔断机制，防止恶意攻击和系统过载',
            'category': '安全',
            'source': '技术团队',
            'status': 'pending'
        },
        {
            'id': 8,
            'title': '实时数据同步',
            'description': '实现多端数据实时同步，支持 WebSocket 长连接，确保数据一致性',
            'category': '性能',
            'source': '产品规划',
            'status': 'pending'
        }
    ]


if __name__ == '__main__':
    # 测试代码
    analyzer = RequirementAnalyzer()
    sample_data = create_sample_requirements()
    df = analyzer.import_from_dict(sample_data)
    df = analyzer.classify_all()
    print(analyzer.get_statistics())
