from fastapi import APIRouter

from .challan import router as challan_router
from .taxinvoice import router as invoice_router
from .pdf_filepath import router as pdffilepath_router
from .bulkpdfpath import router as bulkpdfpath_router
from .pdf_split import router as pdf_split_router
from .pdf_splitb64 import router as pdf_splitb64_router
from .invoice_base64 import router as invoice_base64_router
from .esicchallan import router as esic_router
from .image import router as image_router

router = APIRouter()

router.include_router(challan_router, prefix="/pf", tags=["PF Challan"])
router.include_router(invoice_router, prefix="/invoice", tags=["Invoice"])
router.include_router(pdffilepath_router, prefix="/pdf-filepath", tags=["PDF Filepath"])
router.include_router(bulkpdfpath_router, prefix="/bulk-pdf", tags=["Bulk PDF"])

# ✅ CLEAN endpoints
router.include_router(pdf_split_router, prefix="/pdf-split")
router.include_router(pdf_splitb64_router, prefix="/pdf-split-b64")

router.include_router(invoice_base64_router, prefix="/invoice-base64")
router.include_router(esic_router, prefix="/esic")
router.include_router(image_router, prefix="/image")