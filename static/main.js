const socket = io();
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

let sid, players={}, enemies=[], bullets=[], enemy_bullets=[], powerups=[], particles=[], wave=1;
let shakeTime = 0;

socket.on("init", data=>{
    sid = data.sid;
    players = data.players;
    enemies = data.enemies;
    powerups = data.powerups;
    particles = data.particles;
});

socket.on("update_game", data=>{
    players = data.players;
    enemies = data.enemies;
    bullets = data.bullets;
    enemy_bullets = data.enemy_bullets;
    powerups = data.powerups;
    particles = data.particles;
    wave = data.wave;
    if(enemy_bullets.length>0) shakeTime=3;
});

let keys = {};
document.addEventListener("keydown", e=>keys[e.code]=true);
document.addEventListener("keyup", e=>keys[e.code]=false);

let shooting = false;
document.addEventListener("keydown", e=>{ if(e.code==="Space") shooting=true });
document.addEventListener("keyup", e=>{ if(e.code==="Space") shooting=false });

function gameLoop(){
    ctx.save();

    // screen shake
    if(shakeTime>0){
        ctx.translate(Math.random()*10-5, Math.random()*10-5);
        shakeTime--;
    }

    ctx.clearRect(0,0,800,600);

    let p = players[sid];
    if(p){
        if(keys["KeyA"]) p.x-=5;
        if(keys["KeyD"]) p.x+=5;
        if(keys["KeyW"]) p.y-=5;
        if(keys["KeyS"]) p.y+=5;
        socket.emit("move",{x:p.x,y:p.y});
        if(shooting) socket.emit("shoot",{x:p.x,y:p.y});
    }

    // Particles
    for(let part of particles){
        ctx.fillStyle="orange";
        ctx.fillRect(part.x,part.y,4,4);
    }

    // Players
    for(let id in players){
        let pl = players[id];
        ctx.fillStyle = id===sid?"cyan":"white";
        ctx.fillRect(pl.x-10,pl.y-10,20,20);
        ctx.fillStyle="red";
        ctx.fillRect(pl.x-15,pl.y-20,30*(pl.health/100),5);
    }

    // Enemies
    for(let e of enemies){
        ctx.fillStyle = e.type==="boss"?"orange":"red";
        ctx.fillRect(e.x-(e.type==="boss"?40:15), e.y-(e.type==="boss"?40:15),
                     e.type==="boss"?80:30,e.type==="boss"?80:30);
        ctx.fillStyle="green";
        ctx.fillRect(e.x-(e.type==="boss"?40:15), e.y-(e.type==="boss"?50:25),
                     (e.type==="boss"?80:30)*(e.health/(e.type==="boss"?300:20)),5);
        if(e.type==="boss"){
            ctx.fillStyle="white";
            ctx.fillText("BOSS", e.x-20, e.y-50);
        }
    }

    // Bullets
    ctx.fillStyle="yellow";
    for(let b of bullets) ctx.fillRect(b.x-5,b.y-5,10,10);

    // Enemy bullets
    ctx.fillStyle="magenta";
    for(let eb of enemy_bullets) ctx.fillRect(eb.x-5,eb.y-5,10,10);

    // Powerups
    for(let pu of powerups){
        ctx.fillStyle = pu.type==="health"?"pink": pu.type==="score"?"blue":"white";
        ctx.fillRect(pu.x-10, pu.y-10, 20,20);
    }

    // Wave info
    ctx.fillStyle="white";
    ctx.fillText("Wave: "+wave,10,20);

    ctx.restore();
    requestAnimationFrame(gameLoop);
}

gameLoop();
