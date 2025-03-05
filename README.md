# 🐍 Python Serverless Product Management 🛠️

**By**: Matthew Enarle  
**Workshop Reference**: [ECloud Valley Workshop - Spring Valley Academy](https://walnut-raccoon-d7a.notion.site/Workshop-Brief-1929d79bc5b580ddbafdd7488c34f605)

---

## 🚀 Overview

A **serverless Python app** to manage products using various **AWS services** like **S3**, **DynamoDB**, **CloudWatch**, and **X-Ray**. This application enables **CRUD operations** on products and leverages AWS for batch processing, monitoring, and performance tracing.

---

## 🌟 Features

- **Create, Modify, Delete Products** via HTTP requests ✍️
- **Batch Product Operations** using **S3 file uploads** 📁
- **Logging & Monitoring** with **CloudWatch** 📊
- **Tracing** using **AWS X-Ray** 🔍
- **CloudWatch Metrics** to track product creations 📈

---

## 🌐 AWS Services Used

- **AWS Lambda**: Serverless functions for product management ⚡
- **Amazon S3**: Event-driven triggers for batch processing 📦
- **Amazon DynamoDB**: Store product data 💾
- **Amazon CloudWatch**: Logs & metric filters 📜
- **AWS X-Ray**: Performance tracing 🕵️‍♂️

---

## 📡 API Endpoints

- **POST `/products`** - Create a product 🆕
- **PUT `/products/{product_id}`** - Modify a product ✏️
- **DELETE `/products/{product_id}`** - Delete a product ❌
- **GET `/products`** - List all products 📃
- **GET `/products/{product_id}`** - Get a single product 🔍
