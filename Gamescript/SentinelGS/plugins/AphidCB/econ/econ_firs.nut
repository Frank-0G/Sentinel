 
 
require("econ.nut");
 class econ_firs extends econ{ 
    constructor() {	
        // Cargo enable order, Needs to be overridden
        num_cargos = 8;
        enable_order = [28, 0, 11, 2, 5, 29, 25, 13];
        enable_populations = [200, 500, 1000, 1500, 2500, 4000, 6000, 9000];
        max_populations = [750, 1250, 2000, 3250, 5000, 7500, 11000, 15000];
        decay_rates = [50, 1000, 250, 1000, 150, 40, 125, 350];
        
        // 'Town accepted' absolute cargo amounts. Needs to be overridden
        accept_rel = [94, 90, 148, 15, 92, 30, 29, 8];
        
        // 'Town produced' absolute cargo amounts. To be overridden -- usually zero. 
        prod_rel = [0,0,0,0,0,0,0,0];

        // 'Town produced' relative factor (get from setting) 
        townprod_fct = 650;
        
        // Add 'produced' to 'accepted' requirement
        tpa = [0,1,0,1,0,0,0,0];        
    }
 
    function getPaxCargo();
    function getMailCargo();
}
function econ_firs::getPaxCargo() {return 1;}
function econ_firs::getMailCargo() {return 3;}
