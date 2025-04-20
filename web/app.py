from flask import Flask
from flask_restful import Api, Resource, reqparse
from flasgger import Swagger

from end_points.wifi_scan import WifiScan

app = Flask(__name__)
api = Api(app)
swagger = Swagger(app)


#adding endpoints
api.add_resource(WifiScan, '/scan_wifi')

if __name__ == '__main__':
    app.run(debug=True)
