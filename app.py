from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import string
import random
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('agg')

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Initialize empty list to store services, relationships, and entity names
services = []
relationships = []
entity_names = {}
graph_structure = []

# Dict containing the potential interactions between services
potential_interactions = {
    "Amazon S3": {
        "Amazon EC2": "s3:GetObject",
        "AWS Lambda": "s3:GetObject",
        "Amazon RDS": "s3:GetObject",
        "Amazon DynamoDB": "s3:GetObject",
        "Amazon Athena": "s3:GetObject",
        "AWS Glue": "s3:GetObject",
        "Amazon Kinesis Firehose": "s3:GetObject",
        "Amazon SNS": "s3:GetBucketNotification",
        "Amazon SQS": "s3:GetBucketNotification",
        "Amazon CloudWatch": "s3:PutBucketLogging"
    },
    "Amazon EC2": {
        "Amazon S3": "s3:PutObject",
        "Amazon DynamoDB": "dynamodb:PutItem",
        "AWS Lambda": "lambda:InvokeFunction",
        "Amazon RDS": "rds:CreateDBInstance",
        "Amazon CloudWatch": "logs:CreateLogStream",
        "Amazon Kinesis Firehose": "firehose:PutRecord",
    },
    "AWS Lambda": {
        "Amazon S3": "s3:PutObject",
        "Amazon DynamoDB": "dynamodb:PutItem",
        "Amazon CloudWatch": "logs:CreateLogStream",
        "Amazon Kinesis Firehose": "firehose:PutRecord",
        "Amazon SQS": "sqs:SendMessage"
    },
    "Amazon RDS": {
        "Amazon S3": "s3:PutObject",
        "Amazon CloudWatch": "logs:CreateLogStream",
    },
    "Amazon DynamoDB": {
        "Amazon CloudWatch": "logs:CreateLogStream",
        "AWS Lambda": "lambda:InvokeFunction",
    },
    "Amazon API Gateway": {
        "AWS Lambda": "lambda:InvokeFunction",
        "Amazon Kinesis": "kinesis:PutRecord",
        "Amazon CloudWatch": "logs:CreateLogStream",
        "Amazon Kinesis Firehose": "firehose:PutRecord",
    },
    "Amazon CloudFront": {
        "Amazon CloudWatch": "logs:CreateLogStream",
    },
    "Amazon CloudWatch": {},
    "AWS Glue": {
        "Amazon S3": "s3:PutObject",
        "Amazon DynamoDB": "dynamodb:PutItem",
    },
    "AWS Step Functions": {
        "AWS Lambda": "lambda:InvokeFunction",
    },
    "Amazon Kinesis": {
        "Amazon S3": "s3:PutObject",
        "Amazon DynamoDB": "dynamodb:PutItem",
        "Amazon CloudWatch": "logs:CreateLogStream",
    },
    "Amazon Kinesis Firehose": {
        "Amazon S3": "s3:PutObject",
        "Amazon CloudWatch": "logs:CreateLogStream",
    },
    "Amazon SNS": {
        "Amazon SQS": "sqs:SendMessage",
        "AWS Lambda": "lambda:InvokeFunction",
    },
    "Amazon SQS": {
        "AWS Lambda": "lambda:InvokeFunction",
    },
    "Amazon Athena": {
        "Amazon S3": "s3:GetObject",
        "Amazon CloudWatch": "logs:CreateLogStream",
    },
    "Amazon Elasticsearch Service": {
        "Amazon S3": "s3:PutObject",
        "Amazon Kinesis Firehose": "firehose:PutRecord",
        "Amazon CloudWatch": "logs:CreateLogStream",
    },
}

# List containing supported AWS services
available_services = ["Amazon S3", "Amazon EC2", "AWS Lambda", "Amazon RDS", "Amazon DynamoDB",
                      "Amazon API Gateway", "Amazon CloudFront", "Amazon CloudWatch", "AWS Glue",
                      "AWS Step Functions", "Amazon Kinesis", "Amazon Kinesis Firehose",
                      "Amazon SNS", "Amazon SQS", "Amazon Athena", "Amazon Elasticsearch Service"]

# Keep track of count of each service
service_counts = {}


# Get the ARN for a service instance.
def get_service_arn(service):
    service_to_arn = {
        "Amazon S3": "arn:aws:s3:::",
        "Amazon EC2": "arn:aws:ec2:::instance/",
        "AWS Lambda": "arn:aws:lambda:::function:",
        "Amazon DynamoDB": "arn:aws:dynamodb:::table/",
        "Amazon RDS": "arn:aws:rds:::db:",
        "Amazon API Gateway": "arn:aws:apigateway:::",
        "Amazon CloudWatch": "arn:aws:logs:::log-group:",
        "AWS Glue": "arn:aws:glue:::job/",
        "AWS Step Functions": "arn:aws:states:::stateMachine:",
        "Amazon Kinesis": "arn:aws:kinesis:::stream/",
        "Amazon Kinesis Firehose": "arn:aws:firehose:::deliverystream/",
        "Amazon SNS": "arn:aws:sns:::",
        "Amazon SQS": "arn:aws:sqs:::",
        "Amazon Athena": "arn:aws:athena:::workgroup/",
        "Amazon Elasticsearch Service": "arn:aws:es:::domain/",
        "Amazon CloudFront": "arn:aws:cloudfront:::distribution/"
    }
    service_name, count = service.split(" #")
    ent_name = entity_names[service]
    if ent_name == service:
        return service_to_arn[service_name] + "*"
    else:
        return service_to_arn[service_name] + ent_name


# Generates unique id for each relationship
def generate_relationship_id():
    prefix = random.choice(string.ascii_letters) + '-'
    digits = ''.join(random.choice(string.digits) for _ in range(4))
    return prefix.lower() + digits


@app.route('/get_available_services', methods=['GET'])
def get_available_services():
    return jsonify(services=available_services), 200


@app.route('/add_service', methods=['POST'])
def add_service():
    service = request.json['service']
    name = request.json['name']  # Get name from the request
    # Get the count for this service
    count = service_counts.get(service, 0) + 1
    service_counts[service] = count
    id = service + " #" + str(count)
    name = name.replace(" ", "-")
    name = name.replace("'", "")
    name = name.lower()
    if name != "*":
        entity_names[id] = name  # Store the name in the dictionary
    else:
        entity_names[id] = id
    services.append(id)
    return jsonify(services=services, entity_names=entity_names), 200


@app.route('/delete_service', methods=['POST'])
def delete_service():
    service = request.json['service']
    services.remove(service)
    service_arn = get_service_arn(service)
    new_relationships = []
    for rel in relationships:
        if service_arn == rel['policy']['Statement']['Principal']['AWS']:
            continue
        elif service_arn == rel['policy']['Statement']['Resource']:
            continue
        else:
            new_relationships.append(rel)
    indexes = []
    c = 0
    for rel in graph_structure:
        if rel[0] == entity_names[service] or rel[1] == entity_names[service]:
            indexes.append(c)
        c += 1
    print(graph_structure, indexes)
    for i in reversed(indexes):
        graph_structure.pop(i)
    print(graph_structure, indexes)
    relationships.clear()
    for element in new_relationships:
        relationships.append(element)
    return jsonify(services=services, relationships=new_relationships), 200


@app.route('/create_relationship', methods=['POST'])
def create_relationship():
    source = request.json['source']
    target = request.json['target']

    if source == target:
        return jsonify(error='An entity cannot have a relationship with itself.'), 400

    source_service = source.split(' #')[0]
    target_service = target.split(' #')[0]
    if target_service not in potential_interactions.get(source_service, {}):
        return jsonify(error=f'No potential interaction from {source_service} to {target_service}.'), 400
    action = potential_interactions[source_service][target_service]

    graph_structure.append((entity_names[source], entity_names[target]))

    if source_service == "Amazon S3" and target_service != "Amazon CloudWatch":
        temp = source
        source = target
        target = temp

    relationship_id = generate_relationship_id()
    relationships.append({
        'policy': {
            'Id': relationship_id,
            'Version': '2023-04-23',
            'Statement': {
                'Effect': 'Allow',
                'Principal': {
                    'AWS': get_service_arn(source),
                },
                'Action': action,
                'Resource': get_service_arn(target)
            }
        }
    })
    return jsonify(relationships=relationships), 200


@app.route('/delete_relationship', methods=['POST'])
def delete_relationship():
    index = request.json['index']
    del graph_structure[int(index)]
    del relationships[int(index)]
    return jsonify(relationships=relationships), 200


@app.route('/delete_all_services', methods=['POST'])
def delete_all_services():
    services.clear()
    service_counts.clear()
    entity_names.clear()
    relationships.clear()
    graph_structure.clear()
    return jsonify(services=services, relationships=relationships), 200


@app.route('/delete_all_relationships', methods=['POST'])
def delete_all_relationships():
    relationships.clear()
    graph_structure.clear()
    return jsonify(relationships=relationships), 200


@app.route('/get_graph', methods=['GET'])
def get_graph():
    G = nx.DiGraph()
    for relationship in graph_structure:
        source = relationship[0]
        target = relationship[1]
        G.add_edge(source, target)
    layout = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(15.5, 6))
    ax = plt.gca()
    nx.draw(G, layout, with_labels=False, arrows=True, node_color='lightblue', node_size=500, width=1.5,
            edge_color='gray', ax=ax)
    node_labels = {node: node if node not in entity_names else entity_names[node] for node in G.nodes()}
    node_label_pos = {node: (pos[0], pos[1]) for node, pos in layout.items()}  # Adjust label position
    nx.draw_networkx_labels(G, node_label_pos, labels=node_labels, font_size=7, font_weight='bold', ax=ax)
    ax.margins(0.15)
    plt.savefig('static/graph.png', bbox_inches='tight')
    return jsonify(url='../static/graph.png'), 200


@app.route('/')
def index():
    return render_template('index.html', services=services, relationships=relationships)


if __name__ == '__main__':
    app.run(debug=True)
