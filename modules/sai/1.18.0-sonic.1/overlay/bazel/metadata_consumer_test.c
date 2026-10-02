/* Exercise the public API and generated metadata from an external module. */
#include <stdio.h>
#include <string.h>
#include "sai.h"
#include "saimetadata.h"
#include "saimetadatautils.h"

int main(void)
{
    const sai_attr_metadata_t *attribute;
    const sai_object_type_info_t *object;
    attribute = sai_metadata_get_attr_metadata(SAI_OBJECT_TYPE_PORT, SAI_PORT_ATTR_ADMIN_STATE);
    object = sai_metadata_get_object_type_info(SAI_OBJECT_TYPE_PORT);
    if (SAI_API_VERSION != SAI_VERSION(1, 18, 0) || !attribute || !object ||
        strcmp(attribute->attridname, "SAI_PORT_ATTR_ADMIN_STATE") != 0 ||
        attribute->attrvaluetype != SAI_ATTR_VALUE_TYPE_BOOL ||
        object->objecttype != SAI_OBJECT_TYPE_PORT)
    {
        fprintf(stderr, "SAI public headers or generated metadata are inconsistent\n");
        return 1;
    }
    if (sai_metadata_get_attr_metadata(SAI_OBJECT_TYPE_NULL, 0) != NULL)
    {
        fprintf(stderr, "invalid SAI object unexpectedly has metadata\n");
        return 1;
    }
    puts("SAI 1.18.0 API consumer linked and queried generated metadata");
    return 0;
}
