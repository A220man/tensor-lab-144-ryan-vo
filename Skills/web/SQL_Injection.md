---
name: SQL Injection
category: web
version: "1.0.0"
---

# SKILL: SQL Injection
## Description
SQL injection flaws allow attackers to execute arbitrary SQL code against the application's database by manipulating input parameters. This can lead to data exfiltration, authentication bypass, and data corruption.

## Vulnerable Pattern
```sql
SELECT * FROM users WHERE username = '$input';
```

## Remediation
Use parameterized queries and prepared statements.
