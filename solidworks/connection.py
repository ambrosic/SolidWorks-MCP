"""
SolidWorks Connection Management
Handles connection to SolidWorks application and template management
"""

import win32com.client
import pythoncom
import glob
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class SolidWorksConnection:
    """Manages connection to SolidWorks application"""
    
    def __init__(self):
        self.app = None
        self.template_path = None
        
    def connect(self) -> bool:
        """Connect to SolidWorks application"""
        try:
            # Try to connect to existing instance
            try:
                self.app = win32com.client.GetActiveObject("SldWorks.Application")
                logger.info("Connected to existing SolidWorks instance")
            except:
                # Launch new instance and wait for it to be ready
                logger.info("SolidWorks not running, launching new instance...")
                self.app = win32com.client.Dispatch("SldWorks.Application")
                self.app.Visible = True
                for i in range(30):
                    try:
                        _ = self.app.RevisionNumber
                        logger.info("SolidWorks instance is ready")
                        break
                    except Exception:
                        logger.info(f"Waiting for SolidWorks to start ({i+1}/30)...")
                        time.sleep(1)
                else:
                    raise Exception("SolidWorks failed to start within 30 seconds")

            version = self.app.RevisionNumber
            logger.info(f"SolidWorks version: {version}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to SolidWorks: {e}")
            self.app = None
            return False
    
    def find_template(self) -> Optional[str]:
        """Find Part template automatically"""
        if self.template_path:
            return self.template_path
        
        search_patterns = [
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.prtdot",
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS *\templates\Part.PRTDOT",
        ]
        
        for pattern in search_patterns:
            templates = glob.glob(pattern)
            if templates:
                self.template_path = templates[0]
                logger.info(f"Found template: {self.template_path}")
                return self.template_path
        
        logger.error("No Part template found")
        return None
    
    def create_new_part(self):
        """Create a brand new part document"""
        template = self.find_template()
        if not template:
            raise Exception("No Part template found")
        
        logger.info("Creating new part document")
        doc = self.app.NewDocument(template, 0, 0, 0)
        
        if not doc:
            raise Exception("Failed to create part document")
        
        logger.info("✓ New part document created")
        return doc
    
    def get_active_doc(self):
        """Get the currently active document"""
        return self.app.ActiveDoc if self.app else None
    
    def ensure_connection(self):
        """Ensure we have an active connection"""
        if not self.app:
            if not self.connect():
                raise Exception("Failed to connect to SolidWorks")