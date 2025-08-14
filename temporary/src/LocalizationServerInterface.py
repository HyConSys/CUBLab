import RESTApiClient

class LocalizationServerInterface():
    def __init__(self, url):
        self.rest_client = RESTApiClient.RESTApiClient(url)

    # given the name of the rigid body, get its state (x,y,theta,v)
    def getRigidBodyState(self, rbName):
        response = self.rest_client.restGETjson("?RigidBody="+rbName)
        return response[rbName]

    def get_hyper_rec_str(self, item_type):

        response = self.rest_client.restGETjson()
        return_list = []

        # item[0] = name, item[1] = "untracked" or will be list of values
        for item in response.items():
            is_passed = False
            if item[1] != "untracked":

                values = item[1].split(',')
                x = values[1]
                y = values[2]
                width = values[5]
                width = float(width)
                height = values[6]
                height = float(height)

                if "Target" in item[0] and "Target" == item_type: # is a target
                    x_1 = "{:.4f}".format(float(x) - width/2)
                    x_2 = "{:.4f}".format(float(x) + width/2)
                    y_1 = "{:.4f}".format(float(y) - height/2)
                    y_2 = "{:.4f}".format(float(y) + height/2)
                    theta_v = "{-3.2,3.2},{0.0,0.8}"

                elif "Obstacle" in item[0] and "Obstacle" == item_type: # is an obstacle
                    x_1 = "{:.4f}".format(float(x) - width/2)
                    x_2 = "{:.4f}".format(float(x) + width/2)
                    y_1 = "{:.4f}".format(float(y) - height/2)
                    y_2 = "{:.4f}".format(float(y) + height/2)
                    theta_v = "{-3.2,3.2},{-2.1,2.1}"

                else:
                    is_passed = True
                    pass
                if (is_passed == False):
                    return_string = "{" + str(x_1) + "," + str(x_2) + "},{" + str(y_1) + "," + str(y_2) + "}," + theta_v
                    return_list.append((item[0], return_string))
                    
        return return_list  
