from flask import jsonify
from analytics import TrendAnalytics

class APIRoutes:
    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.trend_analytics = TrendAnalytics(db)
        self.register_routes()
        
    def register_routes(self):
        @self.app.route('/api/trends/<keyword>')
        @self.app.route('/api/trends/<keyword>?days=<days>')
        def get_trend_data(keyword, days=90):
            try:
                # Convert days to integer
                days = int(request.args.get('days', days))
                
                # Get trend data
                trend_data = self.trend_analytics.get_trend_data(keyword, days)
                if not trend_data:
                    return jsonify({"error": f"No trend data found for '{keyword}'"}), 404
                
                # Generate chart
                chart_image = self.trend_analytics.generate_trend_chart(trend_data)
                
                return jsonify({
                    "trend_data": trend_data,
                    "chart_image": chart_image
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
                
        @self.app.route('/api/competitors/<keyword>')
        def get_competitors(keyword):
            try:
                competitor_data = self.trend_analytics.get_competitive_analysis(keyword)
                if not competitor_data:
                    return jsonify({"error": f"No competitor data found for '{keyword}'"}), 404
                    
                return jsonify(competitor_data)
            except Exception as e:
                return jsonify({"error": str(e)}), 500