import logging
import pathlib
from dataclasses import dataclass
from socketserver import StreamRequestHandler
import typing as t
import click
import socket
import os
import io

import subprocess
import string
import random
import time
import gzip
import shutil

import http_messages as httpm

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def eat_messages(stream : io.BytesIO, total_cnt : int, output_stream : io.BytesIO = None, buffer_size : int = 8 * 8 * 1024 * 1024 ):
    # logger.info("eating started")

    buffer_size = min(buffer_size, total_cnt)
    while buffer_size > 0:
        buffer_size = min(buffer_size, total_cnt)
        total_cnt -= buffer_size
        b = stream.read(buffer_size)
        if output_stream is not None:
            output_stream.write(b)
        # logger.info("Another read, left: " + str(total_cnt) + " Buffer cnt: " + str(buffer_size))

    # logger.info("eating ended")

def get_random_string(length: int) -> str:
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    print("Random string of length", length, "is:", result_str)

def get_temp_file_name(length : int, path : str) -> str:
    name = get_random_string(length)




@dataclass
class HTTPServer:
    server_address: t.Tuple[str, int]
    socket: socket.socket
    server_domain: str
    working_directory: pathlib.Path


class HTTPHandler(StreamRequestHandler):
    server: HTTPServer

    # Use self.rfile and self.wfile to interact with the client
    # Access domain and working directory with self.server.{attr}
    def handle(self) -> None:

        # pass

        req = httpm.HTTPRequest.from_bytes(self.rfile)
        # logger.info("req done")

        # self.wfile.write(b'123')

        ###################################################################
        logger.info("Directory: " + self.server.working_directory.as_posix())
        logger.info("Bytes: ")
        logger.info("Method: " + req.method)
        logger.info("Path: " + req.path)
        logger.info("Version: " + req.version)
        logger.info(req.headers)
        ###################################################################
        

        response = httpm.HTTPResponse(version=req.version, status="", headers={})

        total_path = os.path.join(self.server.working_directory.as_posix(), req.path[1:])

        response.version = req.version
        response.headers[httpm.HEADER_SERVER] = "My precious server"

        logger.info("Checking domain...")


        if self.server.server_domain and req.headers[httpm.HEADER_HOST] != self.server.server_domain:
                logger.info("Bad domain")
                response.status = httpm.BAD_REQUEST
                if req.headers.get(httpm.HEADER_CONTENT_LENGTH) is not None:
                    eat_messages(self.rfile, int(req.headers[httpm.HEADER_CONTENT_LENGTH]))

                response.headers[httpm.HEADER_CONTENT_LENGTH] = str(0)
                response.to_bytes(self.wfile)
                return


        if req.method == httpm.GET:
            logger.info("method == GET")
            

            logger.info("Total path: " + total_path)
            
            # self.rfile.read()
            logger.info("Got message body")

            if os.path.exists(total_path):

                logger.info("path exists maybe")
                
                # response setup (no body) (and CONTENT_LENGTH header)
                response.status = httpm.OK
                response.headers[httpm.HEADER_CONTENT_TYPE] = "text/plain"
                # questionable
                
                # if req.headers.get(httpm.HEADER_ACCEPT_ENCODING, None) == "gzip":
                #     response.headers[httpm.HEADER_CONTENT_ENCODING] = "gzip"

                if(os.path.isdir(total_path)):
                     # execute ls -lA > self.rfile
                    logger.info("file is dir")

                    # temp_file = get_temp_file_name(15, self.server.working_directory)

                    directory = subprocess.run(['ls', '-lA', '--time-style=posix-iso', total_path], stdout=subprocess.PIPE)


                    response.headers[httpm.HEADER_CONTENT_LENGTH] = str(len(directory.stdout))

                    response.to_bytes(self.wfile)
                    self.wfile.write(directory.stdout)

                    # if req.headers.get(httpm.HEADER_ACCEPT_ENCODING) != "gzip":
                    #     logger.info("no zip")
                    #     response.to_bytes(self.wfile)
                    #     self.wfile.write(directory.stdout)
                    #     pass
                    # else:
                    #     logger.info("yes zip")
                    #     req.headers[httpm.HEADER_CONTENT_ENCODING] = "gzip"
                    #     response.to_bytes(self.wfile)
                    #     self.wfile.write(gzip.compress(directory.stdout))

                        # pass
                    logger.info("converted to bytes")

                    pass
                # is file
                elif(os.path.isfile(total_path)): 
                    logger.info("file is file")
                    
                    # body
                    file = open(total_path, mode="rb", encoding=None)

                    if req.headers.get(httpm.HEADER_ACCEPT_ENCODING) == "gzip":
                        response.headers[httpm.HEADER_CONTENT_ENCODING] = "gzip"
                        
                        temp_file_name = "kjbsekhbaekbfljafkbawkjfbakwjbfkha"

                        with open(total_path, 'rb', encoding=None) as f_in:
                            f_out = gzip.open(temp_file_name, 'wb', encoding=None)
                            while True:
                                block = f_in.read(8 * 8 * 1024 * 1024)
                                if block == b'':
                                    break
                                f_out.write(block)

                                logger.info("Another chunk zipped")
                            f_out.close()

                        logger.info("Zipped file")

                        
                        response.headers[httpm.HEADER_CONTENT_LENGTH] = str(os.path.getsize(temp_file_name))
                        new = open(temp_file_name, mode="rb", encoding=None)
                        response.to_bytes(self.wfile)
                        eat_messages(new, int(response.headers[httpm.HEADER_CONTENT_LENGTH]), self.wfile)
                        new.close()
                        os.remove(temp_file_name)
                        pass

                    else:
                        logger.info("File size: " + str(os.path.getsize(total_path)))

                        total_size : int = os.path.getsize(total_path)

                        response.headers[httpm.HEADER_CONTENT_LENGTH] = str(total_size)
                        response.to_bytes(self.wfile)
                        logger.info("converted to bytes")

                        eat_messages(file, total_size, self.wfile)
                        logger.info("Drop body")

                        pass

                    

                    pass

                self.wfile.flush()
                pass
            else:
                logger.info("File does not exist")
                response.status = httpm.NOT_FOUND
                response.to_bytes(self.wfile)

            pass

        elif req.method == httpm.POST:

            logger.info("POST begin")
            
            response.status = httpm.OK
            response.headers[httpm.HEADER_CONTENT_LENGTH] = req.headers[httpm.HEADER_CONTENT_LENGTH]

            status_str = "all good"

            if req.headers.get(httpm.HEADER_CREATE_DIRECTORY) == "True":

                logger.info("Directory header present")

                # all good
                if not os.path.exists(total_path):
                    pathlib.Path.mkdir(pathlib.Path(total_path), parents=True)
                else:
                    status_str = "shit happens"
                    response.status = httpm.CONFLICT
                
                if req.headers.get(httpm.HEADER_CONTENT_LENGTH) is not None:
                    eat_messages(self.rfile, int(req.headers[httpm.HEADER_CONTENT_LENGTH]))
            else:
                
                logger.info("No directory header")
                # all good
                if not os.path.exists(total_path):
                    logger.info("Creating new file")
                    logger.info("Directory: " + os.path.dirname(total_path))

                    if not os.path.exists(os.path.dirname(total_path)):
                        # process = subprocess.Popen(['mkdir', os.path.dirname(total_path)])
                        path = pathlib.Path(os.path.dirname(total_path))
                        pathlib.Path.mkdir(path, parents=True)
                    pathlib.Path.touch(pathlib.Path(total_path))

                    time.sleep(0.001)

                    logger.info("Writing new contents")
                    with open(total_path, mode="bw", encoding=None) as file:
                        eat_messages(self.rfile, int(req.headers[httpm.HEADER_CONTENT_LENGTH]), file)

                else:
                    status_str = "shit happens"
                    response.status = httpm.CONFLICT

                    logger.info("Bad request")

                    if req.headers.get(httpm.HEADER_CONTENT_LENGTH) is not None:
                        eat_messages(self.rfile, int(req.headers[httpm.HEADER_CONTENT_LENGTH]))
            
            response.to_bytes(self.wfile, status_str=status_str)
            pass

        elif req.method == httpm.PUT:
            
            status_str = "all good"
            response.status = httpm.OK
            response.headers[httpm.HEADER_CONTENT_LENGTH] = str(0)

            logger.info("PUT started")
            

            if not os.path.isfile(total_path):
                
                logger.info("such file does not exist")

                response.status = httpm.CONFLICT
                status_str = "shit happens"

                if req.headers.get(httpm.HEADER_CONTENT_LENGTH) is not None:
                    eat_messages(self.rfile, int(req.headers[httpm.HEADER_CONTENT_LENGTH]))

                response.to_bytes(self.wfile)
            else:

                logger.info("such file exists")

                try:
                    with open(total_path, mode="bw", encoding=None) as file:
                        logger.info("opened file")
                        eat_messages(self.rfile, int(req.headers[httpm.HEADER_CONTENT_LENGTH]), file)
                except Exception as e:
                    logger.info(str(e))
                
                logger.info("Got data")
                response.to_bytes(self.wfile)
                pass

        elif req.method == httpm.DELETE:
            response.status = httpm.OK
            response.headers[httpm.HEADER_CONTENT_LENGTH] = str(0)

            if os.path.isdir(total_path):
                if req.headers.get(httpm.HEADER_REMOVE_DIRECTORY) == "True":
                    shutil.rmtree(total_path)
                else:
                    response.status = httpm.NOT_ACCEPTABLE
            elif os.path.isfile(total_path):
                # what if REMOVE_DIRECTORY=True
                # subprocess.run(['rm', total_path])
                os.remove(total_path)
            else:
                response.status = httpm.NOT_FOUND

            response.to_bytes(self.wfile)

            pass

        # self.rfile.close()
        # self.wfile.close()
        pass


@click.command()
@click.option("--host", type=str)
@click.option("--port", type=int)
@click.option("--server-domain", type=str)
@click.option("--working-directory", type=str)
def main(host, port, server_domain, working_directory):
    # TODO: Write your code

    ##############################################################

    if host is None:
        host = os.environ.get('SERVER_HOST', '0.0.0.0')

    if port is None:
        port = os.environ.get('SERVER_PORT', '8080')

    if server_domain is None:
        server_domain = os.environ.get('SERVER_DOMAIN')

    if working_directory is None:
        exit(1)

    ###############################################################

    working_directory_path = pathlib.Path(working_directory)
    # working_directory_path = working_directory

    logger.info(
        f"Starting server on {host}:{port}, domain {server_domain}, working directory {working_directory}"
    )

    # Create a server socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Set SO_REUSEADDR option
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket object to the address and port
    s.bind((host, port))
    # Start listening for incoming connections
    s.listen()

    logger.info(f"Listening at {s.getsockname()}")
    server = HTTPServer((host, port), s, server_domain, working_directory_path)

    while True:
        # Accept any new connection (request, client_address)
        try:
            conn, addr = s.accept()
        except OSError:
            break

        try:
            # Handle the request
            HTTPHandler(conn, addr, server)

            # Close the connection
            conn.shutdown(socket.SHUT_WR)
            conn.close()
        except Exception as e:
            logger.error(e)
            conn.close()


if __name__ == "__main__":
    main(auto_envvar_prefix="SERVER")