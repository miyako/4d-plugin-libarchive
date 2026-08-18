//%attributes = {"invisible":true}
If (Application info.headless)

    test_create_tar_gz
    test_list
    test_extract
    test_zip

    LOG EVENT(Into system standard outputs; "PASS"; Information message)

End if
