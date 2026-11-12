import requests

class CrudTester:
    def __init__(self, base_url):
        self.base_url = base_url
        
    def to_curl(self,request):
        """
            Convert a requests.Request object to a cURL command.
        """
        command = ["curl -X {}".format(request.method.upper())]

        for key, value in request.headers.items():
            header = '-H "{}: {}"'.format(key, value)
            command.append(header)

        if request.body:
            # Decode the body if it's bytes
            body_content = request.body.decode() if isinstance(request.body, bytes) else request.body
            body = "-d '{}'".format(body_content)
            command.append(body)

        command.append('"{}"'.format(request.url))

        return " ".join(command)

    def post_data(self, data, data_id):
        response = requests.post(f"{self.base_url}/{data_id}", json=data)
        self.print_response("Create Data", response)
        print(self.to_curl(response.request))
        print("=" * 50)

    def get_data(self, data_id):
        response = requests.get(f"{self.base_url}/{data_id}")
        self.print_response(f"Read Data (ID: {data_id})", response)
        print(self.to_curl(response.request))
        print("=" * 50)

    def put_data(self, data_id, updated_data):
        response = requests.put(f"{self.base_url}/{data_id}", json=updated_data)
        self.print_response(f"Update Data (ID: {data_id})", response)
        print(self.to_curl(response.request))
        print("=" * 50)
    
    def patch_data(self, data_id, patched_data):
        response = requests.patch(f"{self.base_url}/{data_id}", json=patched_data)
        self.print_response(f"Patch Data (ID: {data_id})", response)
        print(self.to_curl(response.request))
        print("=" * 50)

    def delete_data(self, data_id):
        response = requests.delete(f"{self.base_url}/{data_id}")
        self.print_response(f"Delete Data (ID: {data_id})", response)
        print(self.to_curl(response.request))
        print("=" * 50)

    def print_response(self, operation, response):
        print(f"{operation} - Status Code: {response.status_code}")
        print("Response Body:")
        print(response.text)
        print("=" * 50)

if __name__ == "__main__":
    # Replace 'your_api_url' with the actual API URL you want to test
    api_url = 'http://127.0.0.1:5000'

    # Create an instance of CrudTester
    crud_tester = CrudTester(api_url)

    # Example: Create Data
    create_data_payload = {'bookname': 'bookName', 'authorname': 'authorname'}
    data_id_to_create = 1
    crud_tester.post_data(create_data_payload, data_id_to_create)

    # Example: Read Data
    data_id_to_read = 1  # Replace with an existing data ID
    crud_tester.get_data(data_id_to_read)

    # Example: Update Data
    data_id_to_update = 1  # Replace with an existing data ID
    updated_data_payload = {'bookname': 'newBookName'}
    crud_tester.put_data(data_id_to_update, updated_data_payload)
    
    # Example: Patch Data
    data_id_to_patch = 1  # Replace with an existing data ID
    patched_data_payload = {'extra_data': 'extra data'}
    crud_tester.patch_data(data_id_to_patch, patched_data_payload)

    # Example: Delete Data
    data_id_to_delete = 1  # Replace with an existing data ID
    crud_tester.delete_data(data_id_to_delete)


