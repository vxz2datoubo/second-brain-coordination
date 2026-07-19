# 认知知识管理系统 HTTP API 扩展

# 在 server.py 的 get_routes() 末尾添加以下路由:

            # ========== 认知知识管理系统 API ==========
            '/api/zettel/create': lambda: self.zettel_create(self._last_data),
            '/api/zettel/search': lambda: self.zettel_search(self._last_data),
            '/api/zettel/note': lambda: self.zettel_get_note(self._last_data),
            '/api/zettel/stats': lambda: self.zettel_stats(),
            
            '/api/para/create': lambda: self.para_create(self._last_data),
            '/api/para/items': lambda: self.para_get_items(self._last_data),
            '/api/para/stats': lambda: self.para_stats(),
            '/api/para/report': lambda: self.para_report(),
            
            '/api/review/queue': lambda: self.review_queue(),
            '/api/review/record': lambda: self.review_record(self._last_data),
            '/api/review/stats': lambda: self.review_stats(),
            
            '/api/decision/simulate': lambda: self.decision_simulate(self._last_data),
            '/api/decision/build-trading': lambda: self.decision_build_trading(),
            
            '/api/cross-domain/analyze': lambda: self.cross_domain_analyze(self._last_data),
            '/api/cross-domain/map': lambda: self.cross_domain_map(),
            
            '/api/meta/check': lambda: self.meta_check(self._last_data),
            '/api/meta/assessment': lambda: self.meta_assessment(),
            
            '/api/evolve/consolidate': lambda: self.evolve_consolidate(),
            '/api/evolve/stats': lambda: self.evolve_stats(),
            '/api/evolve/forgotten': lambda: self.evolve_forgotten(),
            
            '/api/cms/report': lambda: self.cms_report(),
            '/api/cms/stats': lambda: self.cms_stats(),
        }

    # ========== Zettelkasten API ==========
    
    def zettel_create(self, data):
        note_id, warnings = _cms.create_atomic_note(
            title=data.get('title', ''),
            content=data.get('content', ''),
            tags=data.get('tags', []),
            source=data.get('source', 'api'),
            importance=int(data.get('importance', 3)),
            para_category=data.get('para_category', '')
        )
        self.send_json({'success': True, 'note_id': note_id, 'warnings': warnings})
    
    def zettel_search(self, data):
        results = _cms.search_and_link(data.get('query', ''), limit=int(data.get('limit', 10)))
        self.send_json({'results': results})
    
    def zettel_get_note(self, data):
        note = _cms.get_note_with_context(data.get('note_id', ''))
        self.send_json(note)
    
    def zettel_stats(self):
        self.send_json(_zettel.get_stats())
    
    # ========== PARA API ==========
    
    def para_create(self, data):
        item_id = _para.create_item(
            para=data.get('para', 'R'),
            category=data.get('category', ''),
            title=data.get('title', ''),
            description=data.get('description', ''),
            tags=data.get('tags', [])
        )
        self.send_json({'success': True, 'item_id': item_id})
    
    def para_get_items(self, data):
        items = _para.get_items_by_para(data.get('para', 'P'))
        self.send_json({'items': items})
    
    def para_stats(self):
        self.send_json(_para.get_stats())
    
    def para_report(self):
        self.send_json({'report': _para.generate_report()})
    
    # ========== 间隔复习 API ==========
    
    def review_queue(self):
        queue = _cms.get_review_queue()
        self.send_json({'queue': queue, 'count': len(queue)})
    
    def review_record(self, data):
        result = _cms.record_review(data.get('note_id', ''), int(data.get('rating', 3)))
        self.send_json(result)
    
    def review_stats(self):
        self.send_json(_spaced.get_stats())
    
    # ========== 决策树 API ==========
    
    def decision_simulate(self, data):
        context = data.get('context', {})
        result = _cms.simulate_decision(context)
        self.send_json(result)
    
    def decision_build_trading(self):
        scenario_id = _decision_tree.build_trading_scenario()
        self.send_json({'success': True, 'scenario_id': scenario_id})
    
    # ========== 跨域联想 API ==========
    
    def cross_domain_analyze(self, data):
        insights = _cms.get_cross_domain_insights(
            topic=data.get('topic', ''),
            context=data.get('context', '')
        )
        self.send_json({'insights': insights})
    
    def cross_domain_map(self):
        self.send_json(_cross_domain.build_concept_map())
    
    # ========== 元认知 API ==========
    
    def meta_check(self, data):
        check = _meta.check_cognitive_bias(
            data.get('text', ''),
            data.get('context', {})
        )
        self.send_json({
            'biases': check.detected_biases,
            'fallacies': check.detected_fallacies,
            'gaps': check.reasoning_gaps,
            'warnings': check.recommendations,
            'confidence_adjustment': check.confidence_adjustment
        })
    
    def meta_assessment(self):
        self.send_json(_meta.get_overall_assessment())
    
    # ========== 知识进化 API ==========
    
    def evolve_consolidate(self):
        result = _cms.consolidate_knowledge()
        self.send_json(result)
    
    def evolve_stats(self):
        self.send_json(_evolver.get_evolution_stats())
    
    def evolve_forgotten(self):
        self.send_json({'forgotten': _evolver.get_forgotten_knowledge()[:10]})
    
    # ========== 认知系统总览 API ==========
    
    def cms_report(self):
        self.send_json({'report': _cms.generate_daily_report()})
    
    def cms_stats(self):
        self.send_json(_cms.get_full_stats())

# ========== 新增 imports (在文件顶部添加) ==========
from core.cognitive_memory_system import CognitiveMemorySystem, get_cognitive_memory_system
from core.zettelkasten import Zettelkasten, get_zettelkasten
from core.para_system import PARASystem
from core.spaced_repetition import SpacedRepetition
from core.decision_tree import DecisionTreeEngine
from core.cross_domain_associator import CrossDomainAssociator
from core.meta_cognition import MetaCognitionEngine
from core.knowledge_evolver import KnowledgeEvolver

# ========== 新增实例初始化 (在文件中部添加) ==========
_cms = get_cognitive_memory_system()
_zettel = get_zettelkasten()
_para = PARASystem()
_spaced = SpacedRepetition()
_decision_tree = DecisionTreeEngine()
_cross_domain = CrossDomainAssociator()
_meta = MetaCognitionEngine()
_evolver = KnowledgeEvolver()
