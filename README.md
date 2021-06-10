## architecture
- src
  - svr
  - ui (manual annotation)
  - spider
    - kg_spider
    - corpus_spider
  - model (assitant annotation)
  - check (check the annotations, write to corpus database)
- resource
  - key
  - user
  - medical_kg
  - corpus
- log


## to do
1. Read input
   - 请求网络数据
   - 数据来的时候是q，但事实上是qa对

2. NER annotation
   - BIEO+IO (inside-outside), inside-outside处理情况如：“小腹为什么这么疼”的“为什么这么”
   - 用户点选，产生BIEO
   - 对BIE中进行再次点选，产生反选效果，得到IO

3. EL annotation
    测试集
   - 使用编辑距离推荐KG中相应概念
   - 如果有推荐的被选中，作为gt
   - 如果没有推荐的被选中，gt为空