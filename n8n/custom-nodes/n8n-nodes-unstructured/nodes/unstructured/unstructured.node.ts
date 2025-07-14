import {
  IExecuteFunctions,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  NodeConnectionType,
  IDataObject
} from 'n8n-workflow';


export class unstructured implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'Parse Documents with Unstructured.io',
    name: 'unstructuredio_text_extraction',
    group: ['transform'],
    version: 1,
    description: 'Extract text from all kinds of documents',
    defaults: {
      name: 'Parse Documents',
    },
    inputs: [NodeConnectionType.Main],
    outputs: [NodeConnectionType.Main],
    properties: [
      {
        displayName: 'File Base64 Data',
        name: 'inputBase64',
        type: 'string',
        default: 'c29tZSBjb250ZW50',   // "some content" in base64
        description: 'Base64 data extracted from a file you want to analyze',
      },
      {
        displayName: 'File Name and Extension',
        name: 'fileName',
        type: 'string',
        default: 'doc.pdf',   
        description: 'File name and extension so the base64 can be correctly decoded',
      },
      {
        displayName: 'Unstructured service url',
        name: 'unstructuredUrl',
        type: 'string',
        default: 'http://localhost:8880',   
        description: 'URL of the unstructured python service',
      },
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];

    for (let i = 0; i < items.length; i++) {

      // get user-entered values from the n8n node interface, that we set up just above
      const input_base64 = this.getNodeParameter('inputBase64', i) as string;
      const file_name = this.getNodeParameter('fileName', i) as string;
      const service_url = this.getNodeParameter('unstructuredUrl', i) as string;
      
    
      // enclose the main bits of code in a try/catch just in case
      try {

        const method: string = 'POST'
        const endpoint = '/parse_documents'
        const url = `${service_url}${endpoint}`;
        const body: any = {
          file_name: file_name,
          input_base64: input_base64
        };

        try {
          const requestOptions: any = {
            method,
            headers: {
              'Content-Type': 'application/json',
            },
            json: true,
          };

          requestOptions.body = body;
          

          let response = await this.helpers.httpRequest({
            ...requestOptions,
            url,
          });

          // update the data we're returning
          returnData.push({
            json: response as IDataObject,
          });
          

        } catch (error) {
          if (error instanceof Error) {
            throw new Error(
              `Bad or no response from the unstructured service: ${error.message}`,
            );
          }
          throw error;
        }


      // throw an error and stop if something goes wrong
      } catch (error) { 
        if (error instanceof Error) {
          throw new Error(`Failed to parse document: ${error.message}`);
        }
        throw error;
      }
    }


    return [returnData];
    
  }
}


