// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.6.12;
library SafeMath {

  /**
  * @dev Multiplies two numbers, throws on overflow.
  */
  function mul(int256 a, int256 b) internal pure returns (int256 c) {
    if (a == 0) {
      return 0;
    }
    c = a * b;
    assert(c / a == b);
    return c;
  }

  /**
  * @dev Integer division of two numbers, truncating the quotient.
  */
  function div(int256 a, int256 b) internal pure returns (int256) {
    // assert(b > 0); // Solidity automatically throws when dividing by 0
    // int256 c = a / b;
    // assert(a == b * c + a % b); // There is no case in which this doesn't hold
    return a / b;
  }

  /**
  * @dev Subtracts two numbers, throws on overflow (i.e. if subtrahend is greater than minuend).
  */
  function sub(int256 a, int256 b) internal pure returns (int256) {
    assert(b <= a);
    return a - b;
  }

  /**
  * @dev Adds two numbers, throws on overflow.
  */
  function add(int256 a, int256 b) internal pure returns (int256 c) {
    c = a + b;
    assert(c >= a);
    return c;
  }
}


// This contract will be used to register nodes.
contract Registration {
    using SafeMath for int256;
    int private nodesCount;
    address public owner;
    mapping(address => bool) public acceptedOracles;
    mapping(address => FLNode) private flNodes;
    mapping(int256 => mapping(address => bool)) public resultsReportedForThisNode;
   
    event NewOracleToReportResultAdded(address oracleAddress);
    event AcceptedNodeEvent(address results_reporter, int256 process_id, address node, int256 reputation);
    event FailedNodeEvent(address results_reporter, int256 process_id, address node, int256 reputation);
    event WithdrwanNodeEvent(address results_reporter, int256 process_id, address node, int256 reputation);
   
    struct FLNode{
        int id;
        int R1;
        int R2;
        int R3;
        int reputation;
        bool registered;
    }
   
    constructor() public{
        nodesCount = 0;
        owner = msg.sender;
    }
   
    // This function is to add oracles, oracles are responsible for reporting evaluations.. 
    // scores for each node participated
    function AddOracleToReportResults(address oracleAddress) public{
        require(msg.sender == owner, "You are not authorized to add oracles");
        require(oracleAddress != owner, "Owner cannot be an oracle");
        acceptedOracles[oracleAddress] = true;
        emit NewOracleToReportResultAdded(oracleAddress);
    }
   
    // This function is used by any node looking forward to register itself.
    function RegisterNode() public {
        require(msg.sender != owner, "Owner cannot be a node");
        require(flNodes[msg.sender].registered == false, "This address is aleardy registered");
        nodesCount.add(1);
        flNodes[msg.sender] = FLNode(nodesCount, 0,0,0,0, true);
    }
   
    // This function is used to calculate the reputation score.
    function calculateReputation(address nodeAddress) private view returns(int){
        int x = flNodes[nodeAddress].R1.sub(flNodes[nodeAddress].R2);
        x = x.mul(100);
        int y = flNodes[nodeAddress].R1.add(flNodes[nodeAddress].R2);
        y = y.add(flNodes[nodeAddress].R3);
        int z = x.div(y);
        return z;
    }  
    
    // This function is used by the FL FLEstablishment SC to check the reputation 
    // of each node, this added cost because of smart contract calling 
    //  another smart contract is to avoid malicous nodes as much as possible.
    function VerifyReputation(address nodeAddress, int256 min_reputation) public returns(bool){
        require(flNodes[nodeAddress].registered == true, "This node is not registered");
        if(flNodes[nodeAddress].reputation >= min_reputation)
        {
            flNodes[nodeAddress].R1.add(1);
            flNodes[nodeAddress].reputation = calculateReputation(nodeAddress);
            return true;
        }
        return false;
    }

    // This is called by the oracle that will report the nodes' evaluations
    function RejectedNode(address nodeAddress, int256 process_id) public {
        require(acceptedOracles[msg.sender], "You are not authorized to report results" );
        require(!resultsReportedForThisNode[process_id][nodeAddress], "Results already reported fot this FL Process and this node");
        flNodes[nodeAddress].R1.sub(1);
        flNodes[nodeAddress].R2.add(1);
        flNodes[nodeAddress].reputation = calculateReputation(nodeAddress);
        resultsReportedForThisNode[process_id][nodeAddress] = true;
        emit FailedNodeEvent(msg.sender, process_id, nodeAddress, flNodes[nodeAddress].reputation);
    }
   
    // This is called by the oracle that will report the nodes' evaluations
    function WithdrawnNode(address nodeAddress, int256 process_id) public {
        require(acceptedOracles[msg.sender], "You are not authorized to report results" );
        require(!resultsReportedForThisNode[process_id][nodeAddress], "Results already reported fot this FL Process");
        flNodes[nodeAddress].R1.sub(1);
        flNodes[nodeAddress].R3.add(1);
        flNodes[nodeAddress].reputation = calculateReputation(nodeAddress);
        resultsReportedForThisNode[process_id][nodeAddress] = true;
        emit WithdrwanNodeEvent(msg.sender, process_id, nodeAddress, flNodes[nodeAddress].reputation);
       
    }
}



contract FLEstablishment{
    using SafeMath for int256;
    Registration public registration;
    int256 private process_count;
   
    mapping(int256 => FLProcess) public fl_processes;
    mapping(int256 => bool) public participationOpen;
    mapping(int256 => bool) public votingClosed;
    mapping(int => bool) uploadUpdatesClosed;
    mapping(int256 => bool) evaluationClosed;
    mapping(int256 => mapping(address => bool)) public participants;
    mapping(int256 => int256) public participants_count;
    mapping(int256 => mapping(address =>  InitialModelProposal)) public initialModelProposals;
    mapping(int256 => mapping(address => bool)) hasVotedForInitialModel;
    mapping(int256 => InitialModelProposal) winingInitialModelProposal;

   
    event FLProcessRegistered(address owner, int256 process_id, string name);
    event Participated(address nodeAddress, int256 process_id);
    event ParticipationEnded(address process_owner, int256 process_id);
    event InitialModelProposed(address proposal_owner, int256 process_id);
    event VotedForInitialModel(address voter, address proposal_owner, int256 process_id);
    event VotingForInitialModelEnded(int256 process_id, int256 count, string cfl, string cfh);
    event ModelUpdatesUpload(address nodeAddress, int256 process_id, string ref, string hash);
    event ModelUpdatesUploadPeriodEnded(address process_owner, int process_id);
    event EvaluationUploaded(address process_owner, int process_id, string evaluation_files);
    event EvaluationEnded(address process_owner, int256 process_id);
    event FinalModelUploaded(address owner, int process_id, string final_model_files); 
     
    struct FLProcess{
        int256 id;
        address owner;
        int256 min_reputation;
        string name;
        string initial_configuration_files_link;
        string initial_configuration_files_hash;
        bool registered;
    }
   
    struct InitialModelProposal{
        string configuration_files_link;
        string configuration_files_hash;
        int256 count;
    }

    constructor(address registration_address) public{
        registration = Registration(registration_address);
        process_count = 0;
    }

    // This function used to create a new FL Process, this node is called the master
    function StartNewFL(int256 minReputation,  string memory name, string memory icfl, string memory icfh) public{
        require(registration.VerifyReputation(msg.sender,0) == true, "You are not registered node");
        fl_processes[process_count] = FLProcess(process_count, msg.sender,minReputation,name, icfl, icfh, true);
        participationOpen[process_count] = true;
        participants[process_count][msg.sender] = true;
        participants_count[process_count].add(1);
        initialModelProposals[process_count][msg.sender] = InitialModelProposal(icfl, icfh, 0);
        emit FLProcessRegistered(msg.sender, process_count, name);
        process_count.add(1);
    }
   
    // This function used to participate in some FL Process
    function Participate(int256 process_id) public{
        require(fl_processes[process_id].registered, "The FL Process does not exist");
        require(participants[process_id][msg.sender] == false,  "Your are registered in this FL Process");
        require(participationOpen[process_id], "The participation period is over");
        require(registration.VerifyReputation(msg.sender, fl_processes[process_id].min_reputation), "Your reputation is lower than required");
        participants[process_id][msg.sender] = true;
        participants_count[process_id].add(1);
        emit Participated(msg.sender, process_id);
    }
   
    // This function is called by the master to end the participation period
    function EndParticipation(int256 process_id) public{
        require(fl_processes[process_id].owner == msg.sender, "You are not the owner of this FL Process");
        participationOpen[process_id] = false;
        emit ParticipationEnded(msg.sender, process_id);
    }
   
    // This function is used to propose new initial model
    function Propose(int256 process_id, string memory cfl, string memory cfh) public{
        require(participants[process_id][msg.sender] == true,  "Your are not registered in this FL Process");
        require(participationOpen[process_id] == false, "Participation period is not over yet");
        initialModelProposals[process_id][msg.sender] = InitialModelProposal(cfl, cfh, 0);
        emit InitialModelProposed(msg.sender, process_id);
    }
   
    // This is a voting function, used to vote for desired intial model configurations
    function Vote(int256 process_id, address proposal_owner) public{
        require(votingClosed[process_id] == false, "Voting period is over");
        require(participants[process_id][msg.sender] == true, "You are not registered in this FL Process");
        require(hasVotedForInitialModel[process_id][msg.sender] == false, "You have voted before");
        initialModelProposals[process_id][proposal_owner].count.add(1);
        if(initialModelProposals[process_id][proposal_owner].count > winingInitialModelProposal[process_id].count){
            winingInitialModelProposal[process_id] = initialModelProposals[process_id][proposal_owner];
        }
        hasVotedForInitialModel[process_id][msg.sender] = true;
        emit VotedForInitialModel(msg.sender, proposal_owner, process_id);
    }
   
    // This function is called by the master to end the voting period
    function EndVotingForInitialModel(int256 process_id) public{
        require(fl_processes[process_id].owner == msg.sender, "You are not the owner of this FL Process");
        votingClosed[process_id] = true;
       
        emit VotingForInitialModelEnded(process_id,winingInitialModelProposal[process_id].count,
                                winingInitialModelProposal[process_id].configuration_files_link,
                                winingInitialModelProposal[process_id].configuration_files_hash);
    }
   
   // This function is used to annouce the model updates uploaded by some participant
    function UploadUpdates(int256 process_id, string memory ref, string memory hash) public{
        require(uploadUpdatesClosed[process_id] == false, "Period to upload updates ended");
        emit ModelUpdatesUpload(msg.sender, process_id, ref, hash);
    }
    
    // This function is called by the master to end the period for Uploading Model Updates
    function EndModelUpdatesUpload(int process_id) public {
        require(fl_processes[process_id].owner == msg.sender, "You are not the owner of this FL Process");
        uploadUpdatesClosed[process_id] = true;
        emit ModelUpdatesUploadPeriodEnded(msg.sender, process_id);
    }
    
    // This function is used to annouce the evaluation uploaded by some participant
    // Oracle will keep listening for these event, download the evaluations 
    // and aggregate them to form the final evaluation score for each node.
    function UploadEvaluation(int process_id, string memory ref) public{
        require(evaluationClosed[process_id] == false, "Period to upload evaluations ended");
        emit EvaluationUploaded(msg.sender, process_id, ref);
    }
   
    // This function is called by the master to end the period for Uploading evaluations
    // Oracles will not accept any further evaluations after this event.
    function EndEvaluation(int process_id) public {
        require(fl_processes[process_id].owner == msg.sender, "You are not the owner of this FL Process");
        evaluationClosed[process_id] = true;
        emit EvaluationEnded(msg.sender, process_id);
    }

    // This function is used to annouce the final global model.
    function UploadFinalModel(int process_id, string memory ref) public{
        require(fl_processes[process_id].owner == msg.sender, "You are not the owner of this FL Process");        
        emit FinalModelUploaded(msg.sender, process_id, ref);
    }
   
}