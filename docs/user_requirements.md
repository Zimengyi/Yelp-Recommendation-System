# Project Requirements Log — Travel-Aware Restaurant Recommender

## Source: 2026-05-01 conversations with Haobo

### Iteration 1 (verbatim user voice 18:29 ET)
> "现在我们讨论出来是要做这个餐厅推荐的一个系统。我在想这个产品形态可以是可以基于这个用户的旅游的攻略，以及周边的地理位置去进行一个推荐...第一个就是基于地理位置推荐...还有一个是基于这个就是用户的地理位置推荐周边的嘛，这肯定这是主界面。然后第二个feature就是基于它的一个trip的一个攻略去进行推荐，比如还能帮他生成推荐完了以后，每个旅旅行旅游点每天的旅行点三餐的一个推荐"

### Iteration 2 (verbatim user voice 18:38 ET) — refined to chatbot/agent form
> "主要的形态还是一个agent的形态，一个拆的agent的形态...除了通用的...LM之外...对话能力之外，然后主要的workflow就是基于我们的recommendation system, 对包括最开始进去的以后，开平的引导推荐的一些周围的餐厅，目前的周榜的餐厅。然后还有就是基于他的对话的需求的内容，去推荐最符合他目的的一些餐厅。然后这是主的feature。然后刚才说的trip plan其实就是第二个...这其实也是这个Cha BOT里边的一个feature，就是可以在这个聊天框上面有一个引导，就是吹plan的一个能力"

## Distilled requirements

**Product form**: Conversational agent (chatbot UI). LLM-backed for dialogue, recommender system as the core tool the LLM calls.

**Capabilities**:
1. **Open-screen guidance** (entry point):
   - Recommend nearby restaurants (geo-based)
   - Show "trending this week" (popularity / freshness)
2. **Conversational intent → recommendation** (main flow):
   - User chats → LLM extracts intent (cuisine, budget, mood, party size, …)
   - Recommender ranks based on user × intent × context
3. **Trip plan generator** (secondary feature, accessed via chat top-bar button):
   - User provides itinerary (or agent helps generate one)
   - System produces 3-meals-per-day per stop with diversity + distance constraints

## What is in scope for ML2 grading

The recommender system (DeepFM-based) is what gets graded against the 8-criterion rubric. Everything else is the demo/product wrapper.

## What is OUT of scope (explicit)

- Production-grade chat UI (demo only — Streamlit/Gradio is enough)
- Real user data / live trip uploads (use Yelp Open Dataset + synthetic itineraries)
- Mobile app, login system, payments
- Multi-language (English-only Yelp reviews)
- Real-time GPS — simulate with fixed lat/lon inputs
