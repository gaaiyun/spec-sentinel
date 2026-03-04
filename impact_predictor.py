"""
影响预测模块 - Impact Predictor
功能：基于历史数据的业务影响预测
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class ImpactPredictor:
    """影响预测器 - 基于历史数据预测需求实现后的业务影响"""
    
    def __init__(self, historical_data: Optional[pd.DataFrame] = None):
        """
        初始化预测器
        
        Args:
            historical_data: 历史数据，包含：
                - feature_*: 各种特征（用户数、功能复杂度等）
                - target: 目标指标（如收入增长、用户增长等）
        """
        self.historical_data = historical_data
        self.models = {}
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.target_column = None
        self.model_performance = {}
    
    def prepare_data(
        self,
        feature_columns: List[str],
        target_column: str,
        test_size: float = 0.2
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        准备训练数据
        
        Args:
            feature_columns: 特征列
            target_column: 目标列
            test_size: 测试集比例
        """
        if self.historical_data is None:
            raise Exception("请提供历史数据")
        
        self.feature_columns = feature_columns
        self.target_column = target_column
        
        # 处理缺失值
        df = self.historical_data[feature_columns + [target_column]].copy()
        df = df.dropna()
        
        X = df[feature_columns]
        y = df[target_column]
        
        # 划分训练测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # 标准化
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return (
            pd.DataFrame(X_train_scaled, columns=feature_columns),
            pd.DataFrame(X_test_scaled, columns=feature_columns),
            y_train,
            y_test
        )
    
    def train_linear_model(self, use_ridge: bool = False, **kwargs) -> Dict:
        """
        训练线性回归模型
        
        Args:
            use_ridge: 是否使用 Ridge 回归
            **kwargs: 传递给模型的参数
        """
        if not self.feature_columns:
            raise Exception("请先调用 prepare_data()")
        
        X_train, X_test, y_train, y_test = self.prepare_data(
            self.feature_columns, self.target_column
        )
        
        if use_ridge:
            model = Ridge(**kwargs)
            model_name = 'Ridge'
        else:
            model = LinearRegression(**kwargs)
            model_name = 'Linear'
        
        model.fit(X_train, y_train)
        
        # 评估
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        performance = {
            'model_name': model_name,
            'train_r2': r2_score(y_train, y_pred_train),
            'test_r2': r2_score(y_test, y_pred_test),
            'train_mse': mean_squared_error(y_train, y_pred_train),
            'test_mse': mean_squared_error(y_test, y_pred_test),
            'coefficients': dict(zip(self.feature_columns, model.coef_)),
            'intercept': model.intercept_ if hasattr(model, 'intercept_') else 0
        }
        
        self.models[model_name] = model
        self.model_performance[model_name] = performance
        
        return performance
    
    def train_random_forest(self, **kwargs) -> Dict:
        """训练随机森林模型"""
        if not self.feature_columns:
            raise Exception("请先调用 prepare_data()")
        
        X_train, X_test, y_train, y_test = self.prepare_data(
            self.feature_columns, self.target_column
        )
        
        model = RandomForestRegressor(random_state=42, **kwargs)
        model.fit(X_train, y_train)
        
        # 评估
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        performance = {
            'model_name': 'RandomForest',
            'train_r2': r2_score(y_train, y_pred_train),
            'test_r2': r2_score(y_test, y_pred_test),
            'train_mse': mean_squared_error(y_train, y_pred_train),
            'test_mse': mean_squared_error(y_test, y_pred_test),
            'feature_importances': dict(zip(self.feature_columns, model.feature_importances_))
        }
        
        self.models['RandomForest'] = model
        self.model_performance['RandomForest'] = performance
        
        return performance
    
    def train_gradient_boosting(self, **kwargs) -> Dict:
        """训练梯度提升模型"""
        if not self.feature_columns:
            raise Exception("请先调用 prepare_data()")
        
        X_train, X_test, y_train, y_test = self.prepare_data(
            self.feature_columns, self.target_column
        )
        
        model = GradientBoostingRegressor(random_state=42, **kwargs)
        model.fit(X_train, y_train)
        
        # 评估
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        performance = {
            'model_name': 'GradientBoosting',
            'train_r2': r2_score(y_train, y_pred_train),
            'test_r2': r2_score(y_test, y_pred_test),
            'train_mse': mean_squared_error(y_train, y_pred_train),
            'test_mse': mean_squared_error(y_test, y_pred_test),
            'feature_importances': dict(zip(self.feature_columns, model.feature_importances_))
        }
        
        self.models['GradientBoosting'] = model
        self.model_performance['GradientBoosting'] = performance
        
        return performance
    
    def cross_validate(self, model_name: str, cv: int = 5) -> Dict:
        """
        交叉验证
        
        Args:
            model_name: 模型名称
            cv: 折叠数
        """
        if model_name not in self.models:
            raise Exception(f"模型 {model_name} 不存在")
        
        df = self.historical_data[self.feature_columns + [self.target_column]].dropna()
        X = df[self.feature_columns]
        y = df[self.target_column]
        
        X_scaled = self.scaler.fit_transform(X)
        
        model = self.models[model_name]
        scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='r2')
        
        return {
            'model_name': model_name,
            'cv_scores': scores.tolist(),
            'mean_r2': scores.mean(),
            'std_r2': scores.std()
        }
    
    def predict_impact(self, feature_values: Dict[str, float], model_name: str = 'RandomForest') -> Dict:
        """
        预测新需求的影响
        
        Args:
            feature_values: 特征值字典
            model_name: 使用的模型
        """
        if model_name not in self.models:
            raise Exception(f"模型 {model_name} 不存在")
        
        # 准备输入数据
        X_new = pd.DataFrame([feature_values], columns=self.feature_columns)
        X_new_scaled = self.scaler.transform(X_new)
        
        model = self.models[model_name]
        prediction = model.predict(X_new_scaled)[0]
        
        # 计算置信区间（使用模型的标准差估计）
        if hasattr(model, 'estimators_'):
            # 随机森林可以使用树的标准差
            predictions = [tree.predict(X_new_scaled)[0] for tree in model.estimators_]
            std = np.std(predictions)
            ci_lower = prediction - 1.96 * std
            ci_upper = prediction + 1.96 * std
        else:
            # 其他模型使用历史残差的标准差
            std = np.sqrt(self.model_performance[model_name]['test_mse'])
            ci_lower = prediction - 1.96 * std
            ci_upper = prediction + 1.96 * std
        
        return {
            'predicted_impact': prediction,
            'confidence_interval_95': (ci_lower, ci_upper),
            'model_used': model_name,
            'model_r2': self.model_performance[model_name]['test_r2']
        }
    
    def get_feature_importance(self, model_name: str = 'RandomForest') -> pd.DataFrame:
        """获取特征重要性"""
        if model_name not in self.models:
            raise Exception(f"模型 {model_name} 不存在")
        
        performance = self.model_performance[model_name]
        
        if 'feature_importances' in performance:
            importance_df = pd.DataFrame({
                'feature': list(performance['feature_importances'].keys()),
                'importance': list(performance['feature_importances'].values())
            })
            importance_df = importance_df.sort_values('importance', ascending=False)
            return importance_df
        elif 'coefficients' in performance:
            importance_df = pd.DataFrame({
                'feature': list(performance['coefficients'].keys()),
                'coefficient': list(performance['coefficients'].values())
            })
            importance_df['abs_coefficient'] = importance_df['coefficient'].abs()
            importance_df = importance_df.sort_values('abs_coefficient', ascending=False)
            return importance_df
        else:
            return pd.DataFrame()
    
    def compare_models(self) -> pd.DataFrame:
        """比较所有训练过的模型"""
        records = []
        for model_name, perf in self.model_performance.items():
            records.append({
                'model': model_name,
                'train_r2': perf['train_r2'],
                'test_r2': perf['test_r2'],
                'test_mse': perf['test_mse'],
                'r2_gap': perf['train_r2'] - perf['test_r2']  # 过拟合程度
            })
        
        return pd.DataFrame(records)
    
    def get_best_model(self) -> str:
        """获取最佳模型"""
        if not self.model_performance:
            raise Exception("请先训练模型")
        
        best_model = max(self.model_performance.items(), key=lambda x: x[1]['test_r2'])
        return best_model[0]


def create_sample_historical_data(n_samples: int = 100) -> pd.DataFrame:
    """创建示例历史数据"""
    np.random.seed(42)
    
    # 生成特征
    data = {
        'user_reach': np.random.randint(100, 10000, n_samples),  # 影响用户数
        'development_effort': np.random.randint(1, 20, n_samples),  # 开发工作量（周）
        'feature_complexity': np.random.randint(1, 10, n_samples),  # 功能复杂度
        'market_demand': np.random.uniform(0.3, 1.0, n_samples),  # 市场需求度
        'competitive_pressure': np.random.uniform(0.1, 1.0, n_samples),  # 竞争压力
        'strategic_alignment': np.random.uniform(0.3, 1.0, n_samples),  # 战略匹配度
    }
    
    df = pd.DataFrame(data)
    
    # 生成目标变量（收入影响，单位：万元）
    # 模拟真实关系：用户越多、需求越高、战略匹配度越高 -> 影响越大
    # 开发 effort 和复杂度越高 -> 成本越高，净影响可能降低
    df['revenue_impact'] = (
        df['user_reach'] * 0.01 * df['market_demand'] * df['strategic_alignment'] *
        (1 + df['competitive_pressure'] * 0.5) -
        df['development_effort'] * 2 -
        df['feature_complexity'] * 1.5 +
        np.random.normal(0, 10, n_samples)  # 噪声
    )
    
    # 确保目标变量为正
    df['revenue_impact'] = df['revenue_impact'].clip(lower=0)
    
    return df


def create_sample_historical_data_classification(n_samples: int = 100) -> pd.DataFrame:
    """创建示例历史数据（分类任务 - 成功/失败）"""
    np.random.seed(42)
    
    data = {
        'rice_score': np.random.uniform(0, 100, n_samples),
        'team_experience': np.random.randint(1, 10, n_samples),
        'budget_adequacy': np.random.uniform(0.3, 1.0, n_samples),
        'stakeholder_support': np.random.randint(1, 5, n_samples),
        'technical_feasibility': np.random.randint(1, 5, n_samples),
    }
    
    df = pd.DataFrame(data)
    
    # 生成目标变量（项目成功概率）
    success_prob = (
        0.3 * (df['rice_score'] / 100) +
        0.2 * (df['team_experience'] / 10) +
        0.2 * df['budget_adequacy'] +
        0.15 * (df['stakeholder_support'] / 5) +
        0.15 * (df['technical_feasibility'] / 5) +
        np.random.normal(0, 0.1, n_samples)
    )
    
    df['success_probability'] = success_prob.clip(0, 1)
    df['success'] = (df['success_probability'] > 0.5).astype(int)
    
    return df


if __name__ == '__main__':
    # 测试代码
    historical_data = create_sample_historical_data(100)
    
    predictor = ImpactPredictor(historical_data)
    
    feature_cols = ['user_reach', 'development_effort', 'feature_complexity', 
                    'market_demand', 'competitive_pressure', 'strategic_alignment']
    target_col = 'revenue_impact'
    
    # 训练多个模型
    predictor.prepare_data(feature_cols, target_col)
    print("线性回归:", predictor.train_linear_model())
    print("\n随机森林:", predictor.train_random_forest(n_estimators=50))
    print("\n梯度提升:", predictor.train_gradient_boosting(n_estimators=50))
    
    # 模型比较
    print("\n模型比较:")
    print(predictor.compare_models())
    
    # 预测新需求
    new_feature = {
        'user_reach': 5000,
        'development_effort': 8,
        'feature_complexity': 6,
        'market_demand': 0.8,
        'competitive_pressure': 0.6,
        'strategic_alignment': 0.9
    }
    
    prediction = predictor.predict_impact(new_feature, 'RandomForest')
    print(f"\n预测影响：{prediction['predicted_impact']:.2f} 万元")
    print(f"95% 置信区间：[{prediction['confidence_interval_95'][0]:.2f}, {prediction['confidence_interval_95'][1]:.2f}]")
