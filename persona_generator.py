"""
用户画像模块 - Persona Generator
功能：基于数据的用户细分和画像生成
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from typing import Dict, List, Optional, Tuple
import json


class PersonaGenerator:
    """用户画像生成器 - 基于行为数据进行用户细分"""
    
    def __init__(self, user_data: pd.DataFrame):
        """
        初始化画像生成器
        
        Args:
            user_data: 用户行为数据，包含用户 ID 和各种行为指标
        """
        self.raw_data = user_data.copy()
        self.processed_data = None
        self.scaler = StandardScaler()
        self.segments = None
        self.personas = []
    
    def preprocess(self, feature_columns: List[str]) -> pd.DataFrame:
        """
        预处理用户数据
        
        Args:
            feature_columns: 用于聚类的特征列
        """
        df = self.raw_data.copy()
        
        # 处理缺失值
        df[feature_columns] = df[feature_columns].fillna(df[feature_columns].median())
        
        # 标准化
        scaled_data = self.scaler.fit_transform(df[feature_columns])
        df_scaled = pd.DataFrame(scaled_data, columns=[f'{col}_scaled' for col in feature_columns])
        
        # 合并数据
        self.processed_data = pd.concat([df.reset_index(drop=True), df_scaled], axis=1)
        
        return self.processed_data
    
    def segment_kmeans(self, n_clusters: int = 4, **kwargs) -> pd.DataFrame:
        """
        使用 K-means 进行用户分群
        
        Args:
            n_clusters: 聚类数量
            **kwargs: 传递给 KMeans 的其他参数
        """
        if self.processed_data is None:
            raise Exception("请先调用 preprocess() 预处理数据")
        
        # 获取标准化后的特征列
        scaled_cols = [col for col in self.processed_data.columns if col.endswith('_scaled')]
        X = self.processed_data[scaled_cols].values
        
        # K-means 聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, **kwargs)
        segments = kmeans.fit_predict(X)
        
        self.processed_data['segment'] = segments
        self.processed_data['segment_label'] = segments.apply(lambda x: f'Segment_{x+1}')
        self.segments = segments
        
        return self.processed_data
    
    def segment_dbscan(self, eps: float = 0.5, min_samples: int = 5) -> pd.DataFrame:
        """
        使用 DBSCAN 进行用户分群（适合发现任意形状的簇）
        
        Args:
            eps: 邻域半径
            min_samples: 最小样本数
        """
        if self.processed_data is None:
            raise Exception("请先调用 preprocess() 预处理数据")
        
        scaled_cols = [col for col in self.processed_data.columns if col.endswith('_scaled')]
        X = self.processed_data[scaled_cols].values
        
        # DBSCAN 聚类
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        segments = dbscan.fit_predict(X)
        
        self.processed_data['segment'] = segments
        self.processed_data['segment_label'] = segments.apply(
            lambda x: f'Cluster_{x+1}' if x >= 0 else 'Noise'
        )
        self.segments = segments
        
        return self.processed_data
    
    def generate_personas(self, feature_columns: List[str]) -> List[Dict]:
        """
        基于分群结果生成用户画像
        
        Args:
            feature_columns: 原始特征列名（非标准化）
        """
        if self.processed_data is None or 'segment' not in self.processed_data.columns:
            raise Exception("请先进行用户分群")
        
        df = self.processed_data
        personas = []
        
        for segment_id in df['segment'].unique():
            if segment_id == -1:  # DBSCAN 的噪声点
                continue
            
            segment_data = df[df['segment'] == segment_id]
            
            # 计算画像特征
            persona = {
                'segment_id': int(segment_id),
                'segment_name': f'用户群_{int(segment_id) + 1}',
                'user_count': len(segment_data),
                'percentage': round(len(segment_data) / len(df) * 100, 2),
                'characteristics': {},
                'behavior_profile': {},
                'recommendations': []
            }
            
            # 计算各特征的平均值
            for col in feature_columns:
                if col in segment_data.columns:
                    mean_val = segment_data[col].mean()
                    std_val = segment_data[col].std()
                    persona['characteristics'][col] = {
                        'mean': round(mean_val, 2),
                        'std': round(std_val, 2)
                    }
            
            # 生成行为画像
            persona['behavior_profile'] = self._generate_behavior_profile(segment_data, feature_columns)
            
            # 生成产品建议
            persona['recommendations'] = self._generate_recommendations(persona)
            
            personas.append(persona)
        
        self.personas = personas
        return personas
    
    def _generate_behavior_profile(self, segment_data: pd.DataFrame, feature_columns: List[str]) -> Dict:
        """生成行为画像描述"""
        profile = {}
        
        # 找出该群体显著高于平均的特征
        overall_mean = segment_data[feature_columns].mean()
        segment_mean = segment_data[feature_columns].mean()
        
        for col in feature_columns:
            if col in segment_data.columns:
                diff_ratio = (segment_mean[col] - overall_mean[col]) / (overall_mean[col] + 0.001)
                if diff_ratio > 0.2:
                    profile[col] = f"显著高于平均 ({diff_ratio:.1%})"
                elif diff_ratio < -0.2:
                    profile[col] = f"显著低于平均 ({diff_ratio:.1%})"
                else:
                    profile[col] = "接近平均"
        
        return profile
    
    def _generate_recommendations(self, persona: Dict) -> List[str]:
        """基于画像生成产品建议"""
        recommendations = []
        
        # 根据用户数量给出优先级
        if persona['percentage'] > 30:
            recommendations.append("这是主要用户群体，应优先满足其需求")
        elif persona['percentage'] > 15:
            recommendations.append("这是重要用户群体，需要重点关注")
        else:
            recommendations.append("这是细分用户群体，可考虑个性化功能")
        
        # 根据特征给出具体建议
        characteristics = persona.get('characteristics', {})
        
        # 示例：如果有使用频率相关指标
        for feature, stats in characteristics.items():
            if 'frequency' in feature.lower() or 'usage' in feature.lower():
                if stats['mean'] > 50:
                    recommendations.append(f"高频用户，适合推出高级功能订阅")
                else:
                    recommendations.append(f"低频用户，需要提升产品吸引力")
                break
        
        return recommendations
    
    def get_segment_summary(self) -> pd.DataFrame:
        """获取分群汇总统计"""
        if self.processed_data is None:
            raise Exception("请先进行用户分群")
        
        summary = self.processed_data.groupby('segment_label').agg({
            'segment': 'count'
        }).reset_index()
        summary.columns = ['segment', 'user_count']
        summary['percentage'] = (summary['user_count'] / summary['user_count'].sum() * 100).round(2)
        
        return summary
    
    def visualize_pca(self, n_components: int = 2) -> Tuple[np.ndarray, np.ndarray]:
        """
        使用 PCA 降维用于可视化
        
        Args:
            n_components: 降维后的维度数
        
        Returns:
            (降维后的数据，各主成分的解释方差比)
        """
        if self.processed_data is None:
            raise Exception("请先进行用户分群")
        
        scaled_cols = [col for col in self.processed_data.columns if col.endswith('_scaled')]
        X = self.processed_data[scaled_cols].values
        
        pca = PCA(n_components=n_components)
        X_pca = pca.fit_transform(X)
        
        return X_pca, pca.explained_variance_ratio_
    
    def export_personas(self, file_path: str) -> None:
        """导出画像数据到 JSON 文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.personas, f, ensure_ascii=False, indent=2)
    
    def get_persona_dataframe(self) -> pd.DataFrame:
        """将画像转换为 DataFrame"""
        if not self.personas:
            raise Exception("请先生成画像")
        
        records = []
        for persona in self.personas:
            record = {
                'segment_id': persona['segment_id'],
                'segment_name': persona['segment_name'],
                'user_count': persona['user_count'],
                'percentage': persona['percentage']
            }
            # 添加特征
            for feature, stats in persona['characteristics'].items():
                record[f'{feature}_mean'] = stats['mean']
            records.append(record)
        
        return pd.DataFrame(records)


def create_sample_user_data(n_users: int = 200) -> pd.DataFrame:
    """创建示例用户行为数据"""
    np.random.seed(42)
    
    # 生成 4 个不同的用户群体
    segments = np.random.choice([0, 1, 2, 3], n_users, p=[0.35, 0.30, 0.20, 0.15])
    
    data = {
        'user_id': range(1, n_users + 1),
        'age': np.random.randint(18, 65, n_users),
        'session_count': np.zeros(n_users, dtype=int),
        'avg_session_duration': np.zeros(n_users),
        'feature_usage_rate': np.zeros(n_users),
        'purchase_amount': np.zeros(n_users),
        'login_frequency': np.zeros(n_users),
        'referral_count': np.zeros(n_users, dtype=int)
    }
    
    # 为不同群体设置不同的行为模式
    for i, segment in enumerate(segments):
        if segment == 0:  # 活跃用户
            data['session_count'][i] = np.random.randint(50, 200)
            data['avg_session_duration'][i] = np.random.uniform(20, 60)
            data['feature_usage_rate'][i] = np.random.uniform(0.6, 0.9)
            data['purchase_amount'][i] = np.random.uniform(100, 500)
            data['login_frequency'][i] = np.random.randint(5, 7)
            data['referral_count'][i] = np.random.randint(2, 10)
        elif segment == 1:  # 普通用户
            data['session_count'][i] = np.random.randint(20, 50)
            data['avg_session_duration'][i] = np.random.uniform(10, 30)
            data['feature_usage_rate'][i] = np.random.uniform(0.3, 0.6)
            data['purchase_amount'][i] = np.random.uniform(20, 100)
            data['login_frequency'][i] = np.random.randint(2, 5)
            data['referral_count'][i] = np.random.randint(0, 3)
        elif segment == 2:  # 低频用户
            data['session_count'][i] = np.random.randint(5, 20)
            data['avg_session_duration'][i] = np.random.uniform(5, 15)
            data['feature_usage_rate'][i] = np.random.uniform(0.1, 0.3)
            data['purchase_amount'][i] = np.random.uniform(0, 50)
            data['login_frequency'][i] = np.random.randint(1, 3)
            data['referral_count'][i] = 0
        else:  # 高价值用户
            data['session_count'][i] = np.random.randint(100, 300)
            data['avg_session_duration'][i] = np.random.uniform(30, 90)
            data['feature_usage_rate'][i] = np.random.uniform(0.7, 1.0)
            data['purchase_amount'][i] = np.random.uniform(500, 2000)
            data['login_frequency'][i] = np.random.randint(6, 7)
            data['referral_count'][i] = np.random.randint(5, 20)
    
    return pd.DataFrame(data)


if __name__ == '__main__':
    # 测试代码
    user_data = create_sample_user_data(200)
    
    generator = PersonaGenerator(user_data)
    feature_cols = ['session_count', 'avg_session_duration', 'feature_usage_rate', 
                    'purchase_amount', 'login_frequency', 'referral_count']
    
    generator.preprocess(feature_cols)
    generator.segment_kmeans(n_clusters=4)
    personas = generator.generate_personas(feature_cols)
    
    print(f"生成了 {len(personas)} 个用户画像")
    for p in personas:
        print(f"\n{p['segment_name']}: {p['user_count']} 用户 ({p['percentage']}%)")
