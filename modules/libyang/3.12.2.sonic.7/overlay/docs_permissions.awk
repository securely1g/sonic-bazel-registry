# Original debhelper dh_fixperms: documentation files 0644, directories 0755.
{
    if ($0 ~ /(^| )type=file( |$)/) {
        sub(/mode=[0-7]+/, "mode=0644")
    } else if ($0 ~ /(^| )type=dir( |$)/) {
        sub(/mode=[0-7]+/, "mode=0755")
    }
}
