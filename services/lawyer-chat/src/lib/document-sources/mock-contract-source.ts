import { DocumentSource, DocumentSearchParams } from './types';
import { CourtDocument, SearchResponse } from '@/types/court-documents';

/**
 * Mock Contract Document Source
 * 
 * Example implementation showing how to add a new document source.
 * This could be replaced with actual API calls to a contract management system.
 */
export class MockContractSource implements DocumentSource {
  readonly sourceId = 'contracts';
  readonly sourceName = 'Contract Documents';
  readonly description = 'Sample contracts and agreements for demonstration';

  // Mock data - in production, this would come from an API
  private mockContracts: CourtDocument[] = [
    {
      id: 1001,
      case: 'ACME Corp Service Agreement',
      type: 'service_agreement',
      judge: 'Legal Dept',  // Repurpose judge field for department
      court: 'Commercial',  // Repurpose court field for contract category
      date_filed: '2024-01-15',
      text_length: 8500,
      preview: 'This Service Agreement is entered into between ACME Corp and...',
      formatted_title: 'ACME Corp - Service Agreement #2024-001',
      document_type_extracted: 'Service Agreement'
    },
    {
      id: 1002,
      case: 'Software License Agreement - CloudTech',
      type: 'license',
      judge: 'IT Dept',
      court: 'Technology',
      date_filed: '2024-02-20',
      text_length: 12000,
      preview: 'This Software License Agreement governs the use of CloudTech software...',
      formatted_title: 'CloudTech License Agreement v2.0',
      document_type_extracted: 'Software License'
    },
    {
      id: 1003,
      case: 'Office Lease Agreement - Downtown Tower',
      type: 'lease',
      judge: 'Facilities',
      court: 'Real Estate',
      date_filed: '2024-03-01',
      text_length: 15000,
      preview: 'This Lease Agreement for office space at Downtown Tower, Suite 500...',
      formatted_title: 'Downtown Tower Lease - Suite 500',
      document_type_extracted: 'Commercial Lease'
    },
    {
      id: 1004,
      case: 'Employee NDA Template',
      type: 'nda',
      judge: 'HR Dept',
      court: 'Employment',
      date_filed: '2024-01-01',
      text_length: 3500,
      preview: 'This Non-Disclosure Agreement is a standard template for employee confidentiality...',
      formatted_title: 'Standard Employee NDA Template',
      document_type_extracted: 'Non-Disclosure Agreement'
    },
    {
      id: 1005,
      case: 'Vendor Supply Agreement - GlobalParts Inc',
      type: 'supply_agreement',
      judge: 'Procurement',
      court: 'Supply Chain',
      date_filed: '2024-02-15',
      text_length: 9800,
      preview: 'This Supply Agreement establishes terms for parts procurement from GlobalParts Inc...',
      formatted_title: 'GlobalParts Supply Agreement 2024',
      document_type_extracted: 'Supply Agreement'
    }
  ];

  private mockFullTexts: Map<number, string> = new Map([
    [1001, `SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into as of January 15, 2024, between ACME Corporation, a Delaware corporation ("Company"), and Service Provider Inc., a California corporation ("Provider").

1. SERVICES
Provider agrees to provide professional consulting services as described in Exhibit A attached hereto and incorporated herein by reference.

2. TERM
This Agreement shall commence on February 1, 2024, and continue for a period of twelve (12) months, unless earlier terminated in accordance with the provisions hereof.

3. COMPENSATION
Company shall pay Provider a monthly retainer of $10,000, payable within thirty (30) days of receipt of invoice.

4. CONFIDENTIALITY
Both parties agree to maintain the confidentiality of any proprietary information disclosed during the term of this Agreement.

5. TERMINATION
Either party may terminate this Agreement upon thirty (30) days written notice to the other party.

[... Additional standard contract terms ...]`],
    [1002, `SOFTWARE LICENSE AGREEMENT

This Software License Agreement is made between CloudTech Solutions ("Licensor") and the purchasing entity ("Licensee").

GRANT OF LICENSE: Licensor grants Licensee a non-exclusive, non-transferable license to use the CloudTech Platform software.

LICENSE RESTRICTIONS: Licensee may not reverse engineer, decompile, or disassemble the software.

[... Additional license terms ...]`]
  ]);

  async searchDocuments(params: DocumentSearchParams): Promise<SearchResponse> {
    let filtered = [...this.mockContracts];

    // Apply filters
    if (params.category) {
      filtered = filtered.filter(doc => 
        doc.judge?.toLowerCase().includes(params.category!.toLowerCase())
      );
    }

    if (params.type) {
      filtered = filtered.filter(doc => 
        doc.type.toLowerCase().includes(params.type!.toLowerCase())
      );
    }

    if (params.min_length) {
      filtered = filtered.filter(doc => doc.text_length >= params.min_length!);
    }

    // Apply pagination
    const offset = params.offset || 0;
    const limit = params.limit || 50;
    const paginated = filtered.slice(offset, offset + limit);

    return {
      total: filtered.length,
      returned: paginated.length,
      offset,
      limit,
      documents: paginated
    };
  }

  async getDocumentText(id: number | string): Promise<string> {
    const docId = typeof id === 'string' ? parseInt(id, 10) : id;
    
    // Return mock full text if available, otherwise generate sample text
    if (this.mockFullTexts.has(docId)) {
      return this.mockFullTexts.get(docId)!;
    }
    
    const doc = this.mockContracts.find(d => d.id === docId);
    if (!doc) {
      throw new Error(`Contract document ${id} not found`);
    }
    
    // Generate sample contract text based on type
    return this.generateSampleText(doc);
  }

  async getDocument(id: number | string): Promise<CourtDocument> {
    const docId = typeof id === 'string' ? parseInt(id, 10) : id;
    const doc = this.mockContracts.find(d => d.id === docId);
    
    if (!doc) {
      throw new Error(`Contract document ${id} not found`);
    }
    
    // Add text field if not present
    if (!doc.text) {
      doc.text = await this.getDocumentText(docId);
    }
    
    return doc;
  }

  async listDocuments(limit = 20): Promise<CourtDocument[]> {
    return this.mockContracts.slice(0, limit);
  }

  async isAvailable(): Promise<boolean> {
    // Mock source is always available
    return true;
  }

  private generateSampleText(doc: CourtDocument): string {
    const templates: Record<string, string> = {
      service_agreement: `SERVICE AGREEMENT\n\nThis Agreement is for ${doc.case}.\n\nTERMS AND CONDITIONS:\n1. Scope of Services\n2. Payment Terms\n3. Confidentiality\n4. Term and Termination\n5. Warranties\n\n[Standard service agreement terms follow...]`,
      license: `LICENSE AGREEMENT\n\nSoftware: ${doc.case}\n\nLICENSE GRANT:\nSubject to the terms of this Agreement, Licensor grants a limited license...\n\n[Standard license terms follow...]`,
      lease: `LEASE AGREEMENT\n\nProperty: ${doc.case}\n\nLEASE TERMS:\n1. Rent Amount\n2. Security Deposit\n3. Term of Lease\n4. Maintenance Responsibilities\n\n[Standard lease terms follow...]`,
      nda: `NON-DISCLOSURE AGREEMENT\n\n${doc.case}\n\nCONFIDENTIAL INFORMATION:\nThe parties agree to protect confidential information...\n\n[Standard NDA terms follow...]`,
      supply_agreement: `SUPPLY AGREEMENT\n\n${doc.case}\n\nSUPPLY TERMS:\n1. Products to be Supplied\n2. Pricing and Payment\n3. Delivery Terms\n4. Quality Standards\n\n[Standard supply agreement terms follow...]`
    };

    return templates[doc.type] || `AGREEMENT\n\n${doc.case}\n\n[Document content]\n\nThis is a sample document for demonstration purposes.`;
  }
}

// Export singleton instance
export const mockContractSource = new MockContractSource();