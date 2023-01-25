# How to start
1. Install Python3.7 via offical package ([link](https://www.python.org/downloads/)) or run the following commands on Unix systems.  
```sudo apt-get install python3.7```

2. Follow the **Project Setup** in the [doc](https://fetch-hiring.s3.amazonaws.com/data-engineer/pii-masking.pdf) to set up required Docker containers

3. Instal required Python packages  
```pip3 install -r requirements.txt```

4. Run the application  
```python3 main.py```  
<br/>

# Development decisions

## 1. How will you read messages from the queue?  
- The program reads the messages from the SQS queue at most 10 messages in a batch, which is a given limitation for Boto3 package.  
- For testing purpose, the program stops when there is no more messages for 30 seconds.  
- In production env, the program can run continuously in the infinite while loop unless an incident happens.  
<br/>

## 2. What type of data structures should be used?  
- After reading the messages from the SQS queue, a list of dictionaries is used to store the messages since the messages are in JSON format.  
<br/>

## 3. How will you mask the PII data so that duplicate values can be identified?  
- The PII data is masked with AES - a symmetric encryption.  
- The duplicated values will still be duplicates after encryption.  
<br/>

## 4. What will be your strategy for connecting and writing to Postgres?  
- The connection to Postgres starts at the beginning of the program, and only closes before the program exits.  
- The program writes the data to Postgres batch by batch based on the messages received.  
<br/>

## 5. Where and how will your application run?  
- Assume the application can be run on a cloud service with the permissions to connect to other required containers.  
<br/>

---
<br/>

# Discussion questions  

## 1. How would you deploy this application in production?  
- The application can be deployed to a cloud container service, such as AWS ECS. 
- Since the connected components are all internal services, the network setting should be set within a private subnet to ensure security.  
<br/>  
  
## 2. What other components would you want to add to make this production ready?  
- The application should respond 'ACK' to SQS queue to ensure no duplicated messages are consumed, and the erroneous messages that cannot be processed should be writted into logs.  
- Data quality check should be added right after reading the messages.  
- Unit tests and CI/CD can be added into deployment process for more efficient and error-free development cycle.  
- Monitoring and logging are required for debugging and incident reports.  
- For security concerns, the sensitive information, such as password, it should be stored safely. The AWS secrets manageer would be a good option.  
<br/>
    
## 3. How can this application scale with a growing dataset?
- Assume the incoming messages increase, need to make use of the auto-scale feature to create more containers to run the applcations.  
- The database needs to support concurrent inserts for multiple applications to write into the database at the same time.  
- If the dataset grows in a significant scale, which may be overwhelming for a relational databases, an alternative database might be considered depending on the usage of the data. For example, some NoSQL databases are more applicable for large datasets.  
<br/>
  
## 4. How can PII be recovered later on?
- PII is masked with AES, a symmetric encryption algorithms. It is feasible To recover the original values if the private key is given.  
<br/>
  
## 5. What are the assumptions you made?
- The messages are error-free and no data quality check is required.  
- No duplicated data is produced and write all the data into the database.  
- The messages are produced at a rate that an application is able to process. 
- All the sensitve information shouldn't be shared in public, such as database.ini.
