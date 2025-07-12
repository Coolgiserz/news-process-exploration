# 事件抽取表示规范 (v1)

> 本文档说明平台内 **事件 (Event)** 的结构化表示、字段说明与预定义枚举。
>
> 版本: 1.0.0  

---

## 1. 通用 JSON 结构
```jsonc
{
  "trigger"   : "发布",              // 句中触发词
  "type"      : "ProductLaunch",      // 事件类型枚举
  "arguments" : [                      // 角色-文本 列表，可为空
    {"role": "主体", "text": "苹果公司"},
    {"role": "客体", "text": "iPhone 15"},
    {"role": "时间", "text": "今日"}
  ],
  "negated"   : false,                // [可选] 是否否定/未发生
  "confidence": 0.92                  // [可选] 0-1 浮点
}
```

### 字段说明
| 字段        | 类型      | 必填 | 说明                                   |
|-------------|-----------|------|----------------------------------------|
| trigger     | string    | √    | 事件中心词 (动词/名词)                |
| type        | string    | √    | 枚举值，见 §2                          |
| arguments   | array     |      | 参与者列表，每项包含 `role` `text`      |
| negated     | bool      |      | 若事件为否定/未发生，则为 true         |
| confidence  | float     |      | 模型置信度，范围 0-1                   |

`arguments.role` 必须来自**角色枚举**，不同事件类型角色不同。

---

## 2. 事件类型 & 角色枚举

| type             | 语义                              | 角色集合                                                   |
|------------------|-----------------------------------|------------------------------------------------------------|
| ProductLaunch    | 新品发布 / 上市                   | 主体 (发布方)、客体 (产品)、时间、地点                    |
| Acquisition      | 收购 / 并购 / 合并                | 买方、卖方、金额、时间                                     |
| Financing        | 融资完成                          | 公司、金额、轮次、投资方、时间                             |
| PersonnelChange  | 人事变动                          | 人员、职务、机构、时间                                     |
| PolicyRelease    | 政策发布                          | 机构、政策、时间、影响领域                                 |
| Partnership      | 战略合作 / 签署协议              | 方1、方2、合作内容、时间                                   |
| Lawsuit          | 诉讼 / 起诉 / 判决                | 原告、被告、金额/刑期、法院、时间                          |

*枚举可在后续版本扩充，但保持向后兼容。*

---

## 3. 版本管理
* 每次变更字段或新增枚举请提升 `schema_version` 并记录 Changelog。
* Processor 写入 `Event.confidence` & `processor_version` 便于比对。

---

## 4. 示例
```jsonc
[
  {
    "trigger": "收购",
    "type": "Acquisition",
    "arguments": [
      {"role": "买方", "text": "微软"},
      {"role": "卖方", "text": "GitHub"},
      {"role": "金额", "text": "75亿美元"},
      {"role": "时间", "text": "周一"}
    ],
    "confidence": 0.95
  }
]
```

---

## 5. FAQ
1. **一文多事件？** 允许一个 `events` 数组包含多条事件。  
2. **字段缺失？** 若抽取不到某角色，可省略。

---

