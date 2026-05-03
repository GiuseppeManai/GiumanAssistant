# Credit Scoring

Modern credit scoring increasingly uses alternative data sources to assess individuals and SMEs.

## Traditional Data
- Bureau scores
- Financial history

## Alternative Data
- Telco data (usage, payments)
- Transaction data
- Behavioral patterns
- Utility payments
- Digital footprint

## Architecture
- Data ingestion from multiple partners
- Identity matching (privacy-preserving)
- Feature engineering (~100–200 features)
- Model training (logistic regression baseline, neural networks for improvement)
- Explainability (SHAP)

## Challenges
- Regulatory compliance (consent, data usage)
- Data quality and coverage
- Explainability for decision transparency

## Goal
Improve access to credit for underbanked and thin-file populations.

## Approach
- Start with interpretable baseline models
- Add complexity only when measurable improvement exists