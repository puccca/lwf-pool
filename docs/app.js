var app = angular.module('delegateApp', []);

app.controller('indexCtrl', function($scope, $http) {
    $scope.accounts = [];
    $scope.lastpayout = 0;
    $scope.nextpayout = 0;
    $scope.weightvote = 0;

    $http.get ('poollogs.json').then (function (res) {
        $scope.lastpayout = res.data.lastpayout * 1000;
        $scope.nextpayout = moment ($scope.lastpayout).add (1, 'week').valueOf();
        $scope.totalweight = res.data.totalweight;
        $scope.totalpaid = res.data.totalpaid;
        $scope.totalpending = res.data.totalpending;
        $scope.accounts = [];

        for (addr in res.data.accounts) {
            var it = res.data.accounts[addr];
            it['address'] = addr;
            $scope.accounts.push (it);
        }
    });

    $http.get ('https://wallet.lwf.io/api/delegates/get?username=YOURDELEGATENAME').then (function (res) {
        $scope.delegate = res.data.delegate;
        $scope.weightvote = res.data.delegate.vote/100000000;
    });
});
