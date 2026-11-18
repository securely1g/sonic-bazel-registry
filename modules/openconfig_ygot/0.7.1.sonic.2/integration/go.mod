module sonic_ygot_consumer

go 1.25.9

require (
 github.com/openconfig/goyang v0.0.0-20200309174518-a00bece872fc
 github.com/openconfig/ygot v0.7.1
)

// Same selected logging revision as the accepted management-common consumer.
replace github.com/golang/glog => github.com/golang/glog v0.0.0-20160126235308-23def4e6c14b
