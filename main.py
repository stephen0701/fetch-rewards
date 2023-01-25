import boto3
import json
from botocore import exceptions
import logging
from psycopg2 import connect, sql, extras, DatabaseError
from cryptography.fernet import Fernet
from os import path
from config import config


class SQS:

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def connect(self):
        self.sqs_client = boto3.client("sqs", endpoint_url="http://localhost:4566", region_name="", aws_access_key_id="", aws_secret_access_key="")

    def receive_messages(self, query_url):
        """
        Retrieve the messages from SQS
        """
        try:
            messages = self.sqs_client.receive_message(
                QueueUrl=query_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=10,
            )

            user_data = []
            for message in messages.get("Messages", []):
                message_body = json.loads(message["Body"])
                user_data.append(message_body)
        except exceptions.ClientError as error:
            self.logger.exception("Couldn't receive messages from queue: %s", messages)
            raise error
        else:
            return user_data

class Mask():

    def gen_key(self):
        """
        Generates a key and save it into a file
        """
        key = Fernet.generate_key()
        with open("mask.key", "wb") as key_file:
            key_file.write(key)
        
    def load_key(self):
        """
        Loads the key from the current directory named `mask.key`
        """
        return open("mask.key", "rb").read()

    def mask_msg(self, user_data):
        """
        Enctypt the IP and device_id values with AEC.
        Parse the integer value of the app_version.
        """

        key = self.load_key()
        f = Fernet(key)
        for data in user_data:
            if 'ip' in data.keys():
                data['masked_ip'] = f.encrypt(bytes(data.get('ip', ''), 'utf-8')).decode()
            if 'device_id' in data.keys():
                data['masked_device_id'] = f.encrypt(bytes(data.get('device_id', ''), 'utf-8')).decode()
            if 'app_version' in data.keys():
                data['app_version'] = data['app_version'].split('.')[0]
        return user_data


class Postgres():
    
    def connect(self):
        """
        Connect to Postgres SQL database
        """

        conn = None
        try:
            # read PostgreSQL connection parameters
            params = config()

            # connect to PostgreSQL server
            self.psql_conn = connect(**params)
            self.psql_cursor = self.psql_conn.cursor()
        except (Exception, DatabaseError) as error:
            print(error)
        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')

    def write(self, user_data, table):
        """
        Write data into PSQL tables
        """

        col_names = ['user_id', 'app_version', 'device_type', 'masked_ip', 'masked_device_id', 'locale']

        values = []
        for data in user_data:
            value = []
            for col in col_names:
                if col not in data or data[col] is None:
                    value.append(None)
                else:
                    value.append(str(data[col]))
            values.append(value)

        fields = ','.join(self.psql_cursor.mogrify("(%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in values)

        query = "INSERT INTO {table} ({col_names}) VALUES %s".format(table=table, col_names=','.join(col_names))
        extras.execute_values(self.psql_cursor, query, values)

        # query = sql.SQL("INSERT INTO {table} ({col_names}) VALUES ({fields});").format(
        #     table=sql.Identifier(table),
        #     col_names=sql.SQL(', ').join(map(sql.Identifier, col_names)),
        #     fields=sql.Identifier(fields)
        # )

        self.psql_conn.commit()

    def close(self):
        """
        Close Postgres SQL connection
        """
        self.psql_cursor.close()
        self.psql_conn.close()

if __name__ == "__main__":

    print("connecting to SQS...")
    sqs = SQS()
    sqs.connect()
    print("SQS connected.")

    mask = Mask()

    print("connecting to Postgres...");
    postgres = Postgres()
    postgres.connect()
    print("Postgres connected.")

    if (not path.exists("mask.key")):
        mask.gen_key()

    # see if there is a blocking function to wait for the messages
    messages = sqs.receive_messages("/000000000000/login-queue")
    print("A batch of SQS messages received.")
    while(len(messages)):
        data = mask.mask_msg(messages)

        # Should check data integrity before writing
        if (len(data)):
            postgres.write(data, "user_logins")
            print("The data is written into Postgres")

        # postgres_cur = postgres.psql_conn.cursor()
        # postgres_cur.execute(sql.SQL(f"SELECT count(*), count(distinct(user_id)), count(distinct(masked_ip)), count(distinct(masked_device_id)) FROM user_logins LIMIT 100;"))
        # res = postgres_cur.fetchall()
        # print(res)

        messages = sqs.receive_messages("/000000000000/login-queue")
        print("A batch of SQS messages received.")
    
    print("No messages exist in SQS")
    postgres.close()
    print("Close the connection to Postgres")
    print("Bye...")