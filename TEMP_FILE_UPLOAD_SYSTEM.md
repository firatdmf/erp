# Temporary File Upload System for Product Creation

## Overview
This system allows users to upload product images during product creation (before `product_id` exists) using the **same File Manager Modal interface** as product edit mode. Files are temporarily stored in Cloudinary and linked to the product upon successful creation. If the user leaves without saving, files are automatically cleaned up.

### Key Feature
**Unified Interface**: Product creation now uses the exact same "Manage Files" modal as product edit, providing:
- Drag & drop upload
- Image previews
- Reordering (drag to reorder in main grid)
- Primary image selection (first image is primary)
- Instant upload feedback

## Architecture

### Flow Diagram
```
Product Create Page
    ↓
User uploads image → temp_upload_file API
    ↓
Cloudinary upload (temp folder)
    ↓
Store URLs in session
    ↓
Show preview to user
    ↓
User clicks "Create Product" → ProductCreate.form_valid()
    ↓
Create ProductFile records
    ↓
Clear session
    ↓
Success!

OR

User closes page → beforeunload event
    ↓
cleanup_temp_files API
    ↓
Delete from Cloudinary
    ↓
Clear session
```

## Components

### 1. Backend APIs

#### **temp_upload_file** (`/marketing/api/temp_upload_file/`)
- **Method**: POST
- **Purpose**: Upload files to Cloudinary before product_id exists
- **Request**:
  - `file`: File to upload
  - `file_type`: 'main_image' or 'variant_image'
  - `variant_temp_id`: (optional) Temporary variant ID
  - `sequence`: Image sequence order
- **Response**:
  ```json
  {
    "success": true,
    "file_data": {
      "url": "https://cloudinary.com/...",
      "public_id": "media/temp_product_files/...",
      "name": "image.jpg",
      "sequence": 0
    }
  }
  ```
- **Session Storage**:
  ```python
  request.session['temp_product_files'] = {
      'main_images': [
          {'url': '...', 'public_id': '...', 'name': '...', 'sequence': 0}
      ],
      'variant_images': {
          'variant_temp_id_1': [
              {'url': '...', 'public_id': '...', 'name': '...', 'sequence': 0}
          ]
      }
  }
  ```

#### **cleanup_temp_files** (`/marketing/api/cleanup_temp_files/`)
- **Method**: POST
- **Purpose**: Delete temporary files from Cloudinary and session
- **Response**:
  ```json
  {
    "success": true,
    "deleted": 3,
    "errors": []
  }
  ```

### 2. Frontend (temp_file_manager.js)

#### Key Functions

**tempUploadFile(file, fileType, variantTempId, container)**
- Uploads file to temporary storage
- Shows upload progress
- Displays preview with delete button
- Sets `hasUnsavedFiles = true`

**tempDeleteFile(publicId, fileType, variantTempId, btn)**
- Removes file from local tracking
- Removes preview from DOM
- Updates `hasUnsavedFiles` flag

**cleanupTempFiles()**
- Called on page unload
- Uses `navigator.sendBeacon()` for reliability
- Triggers cleanup API

**beforeUnloadWarning(e)**
- Shows browser warning if unsaved files exist
- Prevents accidental data loss

**markFilesAsSaved()**
- Called after successful product creation
- Prevents cleanup on redirect

### 3. ProductCreate.form_valid() Integration

```python
def form_valid(self, form):
    with transaction.atomic():
        self.object = form.save()
        
        # Link temporary files from session to product
        temp_files = self.request.session.get('temp_product_files', {})
        if temp_files:
            # Link main product images
            for file_data in temp_files.get('main_images', []):
                ProductFile.objects.create(
                    product=self.object,
                    file_url=file_data['url'],
                    sequence=file_data['sequence'],
                    is_primary=(file_data['sequence'] == 0)
                )
            
            # Store variant images for handle_variants()
            self.temp_variant_images = temp_files.get('variant_images', {})
            
            # Clear session
            del self.request.session['temp_product_files']
            self.request.session.modified = True
```

## User Experience

### Scenario 1: Successful Product Creation
1. User navigates to product create page
2. User clicks "Upload Product Images"
3. Files upload instantly to Cloudinary
4. Preview appears with drag-to-reorder and delete options
5. User fills form and clicks "Create Product"
6. ProductFile records created
7. Session cleared
8. Redirect to product detail page
9. ✅ No cleanup triggered

### Scenario 2: User Abandons Page
1. User uploads images
2. User closes tab/browser
3. `beforeunload` event fires
4. Browser shows warning: "You have uploaded files but haven't saved..."
5. If user confirms exit:
   - `cleanupTempFiles()` called via `sendBeacon()`
   - Cloudinary files deleted
   - Session cleared
6. ✅ No orphaned files

### Scenario 3: User Deletes Image
1. User uploads 3 images
2. User clicks delete on 2nd image
3. Image removed from preview
4. `hasUnsavedFiles` still true (1 image remains)
5. User can continue editing or leave (cleanup will remove remaining)

## Security

1. **Session-based**: Files are tied to user's session
2. **Authenticated**: `@login_required` on all APIs
3. **CSRF Protected**: Uses Django CSRF tokens
4. **Folder Isolation**: Files stored in user-specific temp folders:
   ```
   media/temp_product_files/{username}_{timestamp}/
   ```

## Testing

### Manual Test Cases

#### Test 1: Upload and Create Product
```bash
1. Go to /marketing/product_create/
2. Click "Upload Product Images"
3. Select 2-3 images
4. Wait for uploads to complete
5. Fill required fields (title, SKU)
6. Click "Create Product"
7. Check product detail page shows images
8. Check Cloudinary - files should be in permanent folder
```

#### Test 2: Upload and Abandon
```bash
1. Go to /marketing/product_create/
2. Upload images
3. Try to close tab
4. Browser warning should appear
5. Confirm exit
6. Check Cloudinary - temp files should be deleted
7. Check Django sessions - temp_product_files should be cleared
```

#### Test 3: Delete Before Save
```bash
1. Go to /marketing/product_create/
2. Upload 3 images
3. Delete 1 image using X button
4. Leave page
5. Cleanup should delete remaining 2 images
```

#### Test 4: Multiple Uploads
```bash
1. Upload 2 images
2. Upload 3 more images
3. All 5 should appear in order
4. Drag to reorder
5. Create product
6. Order should be preserved
```

## Files Modified

### Backend
- `erp/marketing/views.py`
  - Added `temp_upload_file()` (line 1443-1498)
  - Added `cleanup_temp_files()` (line 1500-1550)
  - Updated `ProductCreate.form_valid()` (line 753-779)
  
- `erp/marketing/urls.py`
  - Added route: `api/temp_upload_file/`
  - Added route: `api/cleanup_temp_files/`

### Frontend
- `erp/marketing/static/marketing/js/temp_file_manager.js` (NEW)
  - 311 lines
  - Handles upload, delete, cleanup, warnings
  
- `erp/marketing/templates/marketing/product_form.html`
  - Updated product images section (line 158-169)
  - Added script initialization (line 449-486)

## Future Improvements

1. **Variant Images**: Extend to handle variant image uploads during creation
2. **Progress Bar**: Show aggregate progress for multiple uploads
3. **Image Optimization**: Apply Cloudinary transformations on upload
4. **Retry Logic**: Handle failed uploads with retry
5. **Session Cleanup**: Background job to clean old temp files (>24hrs)
6. **Drag Upload**: Support drag-and-drop file upload
7. **Preview Reordering**: Enable drag-to-reorder before save

## Known Limitations

1. Session-based storage means files lost if session expires before save
2. No recovery mechanism if user loses connection during upload
3. Browser compatibility: `sendBeacon()` not supported in IE11
4. No file size validation on frontend (relies on Cloudinary limits)

## Configuration

No additional configuration needed. Uses existing:
- Django sessions
- Cloudinary configuration
- CSRF middleware

## Support

For issues or questions:
- Check browser console for error messages
- Check Django logs for API errors
- Verify Cloudinary credentials are valid
- Ensure session middleware is enabled
